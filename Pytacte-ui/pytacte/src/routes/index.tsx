import { useEffect, useRef, useState, createElement } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { getIfUserLoggedIn } from '../firebase/firebase_auth'
import RootPanel from '#/components/RootPanel'
import CustomAppBar from '#/components/CustomAppBar'
import DeviceSelector from '#/components/DeviceSelector'
import CustomPaper from '#/components/CustomPaper'
import CustomSelectionField from '#/components/CustomSelectionField'
import Typography from '@mui/material/Typography'
import Divider from '@mui/material/Divider'
import IconButton from '@mui/material/IconButton'
import MicOffIcon from '@mui/icons-material/MicOff'
import MicIcon from '@mui/icons-material/Mic'
import OpenInFull from '@mui/icons-material/OpenInFull'
import CloseFullscreen from '@mui/icons-material/CloseFullscreen'
import SaveIcon from '@mui/icons-material/Save';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import LiveWaveformVisualiser from '#/components/LiveWaveformVisualiser'
import CodeMirror from '@uiw/react-codemirror'
import { EditorView } from '@codemirror/view'
import { StartLiveAudioCapture, StopAudioCapture } from '../utils/LiveAudioCapture'
import { getJwtToken } from '../firebase/firebase_auth'
import { jsPDF } from "jspdf";
import '../../fonts/Tiny5-Duo-normal.js';


const transcriptionEditorTheme = EditorView.theme({
  '&': {
    height: '100%',
    color: '#f8f8f8',
    backgroundColor: '#003b5f',
    fontFamily: '"Tiny5 Duo", sans-serif',
    fontSize: '0.95rem',
  },
  '&.cm-focused': { outline: 'none' },
  '.cm-scroller': {
    overflow: 'auto',
    fontFamily: 'inherit',
    lineHeight: '1.65',
    scrollbarWidth: 'thin',
    scrollbarColor: '#f8f8f8 #003b5f',
  },
  '.cm-content': { padding: '10px', caretColor: '#f8f8f8' },
  '.cm-line': { padding: '0' },
  '.cm-gutters': { display: 'none' },
  '.cm-cursor': { borderLeftColor: '#f8f8f8' },
  '.cm-selectionBackground': { backgroundColor: 'dodgerblue' },
  '.cm-content ::selection': { backgroundColor: 'dodgerblue !important', color: '#fff' },
  '&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground': {
    background: 'dodgerblue !important',
  },
  '.cm-scroller::-webkit-scrollbar': { width: '8px', height: 0 },
  '.cm-scroller::-webkit-scrollbar:horizontal': { display: 'none' },
  '.cm-scroller::-webkit-scrollbar-track': { backgroundColor: '#003b5f', borderRadius: '8px' },
  '.cm-scroller::-webkit-scrollbar-thumb': { backgroundColor: '#f8f8f8', borderRadius: '8px', border: '2px solid #003b5f' },
  '.cm-scroller::-webkit-scrollbar-thumb:hover': { backgroundColor: '#f8f8f8' },
}, { dark: true })

const transcriptionEditorExtensions = [EditorView.lineWrapping, transcriptionEditorTheme]


export const Route = createFileRoute('/')({ component: Home })


function Home() {

  const targetInitMarker = '>>>';
  const targetInitLabel = ' init pytacte';

  const [expandTranscriptionPanel, setExpandTranscriptionPanel] = useState(false);

  const [initLabel, setInitLabel] = useState<string>(targetInitMarker);
  const [hydrated, setHydrated] = useState<boolean>(false);
  let markerAnimationInterval: NodeJS.Timeout | undefined;
  let initLabelValue: string = targetInitMarker;
  let markerIndex: number = 0;

  const [webSocketStreaming, setWebSocketStreaming] = useState<Worker | undefined>(undefined);
  const webSocketStreamingRef = useRef<Worker | undefined>(undefined);

  const shutdownRequestedRef = useRef(false);
  const webWorkerInit = useRef<boolean>(false);

  const jwtValidatationProcedureInitiated = useRef<boolean>(false);
  const jwtValidated = useRef<boolean>(false);

  const modelParamatersValidatationProcedureInitiated = useRef<boolean>(false);
  const modelParamatersValidated = useRef<boolean>(false);

  const [authReady, setAuthReady] = useState<boolean>(false);
  const [muteAudio, setMuteAudio] = useState<boolean>(false);
  const [audioStream, setAudioStream] = useState<MediaStream | null>(null);
  const [modelPanelHeight, setModelPanelHeight] = useState<number>();
  const modelPanelRef = useRef<HTMLDivElement>(null);


  const model = useRef<string>('');
  const precision = useRef<string>('');

  const [currentModel, setCurrentModel] = useState<string>('');
  const [currentPrecision, setCurrentPrecision] = useState<string>('');

  const [modelSelectionEnabled, setModelSelectionEnabled] = useState(true);
  const [precisionSelectionEnabled, setPrecisionSelectionEnabled] = useState(true);




  const transcription = useRef<string>('');
  const [transcriptionValue, setTranscriptionValue] = useState<string>('');

  const [saveDocument, setSaveDocument] = useState<boolean>();
  const [clearTranscription, setClearTranscription] = useState<boolean>();


  function StreamAudioToServer(bytes: ArrayBuffer) {
    if (jwtValidated.current && modelParamatersValidated.current) {
      webSocketStreamingRef.current?.postMessage(bytes);
    }
  }



  function initAnimation() {

    if (markerIndex < targetInitLabel.length) {
      initLabelValue += targetInitLabel[markerIndex];
      setInitLabel(initLabelValue);
      markerIndex++;
    }
    else {
      clearInterval(markerAnimationInterval);
    }
  }


  function sanitizePlainText(value: string): string {
    return value
      .normalize('NFC')
      .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, '')
      .trim();
  }

  function isSymbol(char: string): boolean {
    return /^\p{S}$/u.test(char);
  }


  useEffect(() => {
    getIfUserLoggedIn().then((isUserLoggedIn) => {
      if (isUserLoggedIn) {
        setAuthReady(true);

        if (!hydrated) {
          markerAnimationInterval ?? clearInterval(markerAnimationInterval);
          markerAnimationInterval = setInterval(initAnimation, 100);
          setHydrated(true);
        }
      } else {
        window.location.href = '/auth'
      }
    });
  }, []);



  useEffect(() => {
    if (webSocketStreaming) {
      webSocketStreaming.onmessage = (event: MessageEvent) => {
        const [isStatus, payload] = event.data;
        if (isStatus) {


          if (shutdownRequestedRef.current && String(payload).startsWith('[ Socket closed:')) {
            shutdownRequestedRef.current = false;
            webSocketStreaming.terminate();
            setWebSocketStreaming(undefined);
            webSocketStreamingRef.current = undefined;
            return;
          }

          if (String(payload).includes('[ Socket connected to: ')) {
            webWorkerInit.current = true;

            if (!jwtValidatationProcedureInitiated.current) {
              getJwtToken().then((result) => {
                const successful = result[0]
                const payload = result[1]
                if (successful) {
                  webSocketStreaming?.postMessage(`<Authorisation_Token>${payload}</Authorisation_Token>`);
                  jwtValidatationProcedureInitiated.current = true;
                }
                else {
                }
              });
            }
          }
        } else {


          if (!jwtValidated.current) {
            if (payload === '<JWT_Valid/>') {
              jwtValidated.current = true;

              if (!modelParamatersValidatationProcedureInitiated.current) {
                webSocketStreaming?.postMessage(`<STT_Model>${model.current}</STT_Model><STT_Model_Precision>${precision.current}</STT_Model_Precision>`);
                modelParamatersValidatationProcedureInitiated.current = true;
              }
            }
            else if (payload === '<JWT_Invalid/>' || payload === '<Invalid_Message/>') {

            }
          }
          else {
            if (!modelParamatersValidated.current) {

              if (payload === '<Valid_Model_Parameters/>') {
                modelParamatersValidated.current = true;
              }
              else if (payload === '<Invalid_Model_Parameters/>') {

              }
            }
            else {
              const _message = String(payload);

              if (_message.trim() !== '') {
                const terminator = isSymbol(_message[_message.length - 1]) ? '' : '.';
                const message = `${_message[0].toUpperCase()}${_message.slice(1, _message.length)}${terminator} `;
                transcription.current += message;
                console.log(`[${transcription.current}]`);
                setTranscriptionValue(transcription.current);
              }
            }
          }
        }
      };

      webSocketStreaming.onerror = (event: ErrorEvent) => {
        console.error('Streaming worker error:', event.message);
      };
    }


    if (!webWorkerInit.current && webSocketStreaming) {
      shutdownRequestedRef.current = false;
      const protocol = 'wss';
      webSocketStreaming?.postMessage(['127.0.0.1', '80', protocol]);
      webSocketStreamingRef.current = webSocketStreaming;
    }
    else {
      if (webWorkerInit.current) {
        jwtValidated.current = false;
        jwtValidatationProcedureInitiated.current = false;
        modelParamatersValidated.current = false;
        modelParamatersValidatationProcedureInitiated.current = false;
        webWorkerInit.current = false;
        setWebSocketStreaming(undefined);



        if (webSocketStreaming) {
          webSocketStreaming.onmessage = null;
          webSocketStreaming.onerror = null;
          webSocketStreamingRef.current = undefined;
        }
      }
    }
  }, [webSocketStreaming])


  function InitCapture() {
    StartLiveAudioCapture(StreamAudioToServer, setAudioStream).then(([message, isSuccessful]: [string, boolean]) => {
      console.log('InitCapture message:', message);
      console.log('InitCapture status:', isSuccessful);

      if (isSuccessful) {
        if (isSuccessful) {
          console.log('--> Init connection')
          setMuteAudio(true);
          setModelSelectionEnabled(false);
          setPrecisionSelectionEnabled(false);
          setWebSocketStreaming(new Worker(new URL("../utils/WebSocketWorker.js", import.meta.url)));
        }
      }

    });
  }

  async function StopCapture() {
    const [message, isSuccessful]: [string, boolean] = StopAudioCapture();
    console.log('StopCapture message:', message);
    console.log('StopCapture status:', isSuccessful);

    if (isSuccessful) {
      setAudioStream(null);
      if (isSuccessful) {
        setMuteAudio(false);
        setModelSelectionEnabled(true);
        setPrecisionSelectionEnabled(true);

        // Ask the worker to close the socket. The socket's close status event
        // will be detected above before the worker is terminated.
        if (webSocketStreaming) {
          shutdownRequestedRef.current = true;
          webSocketStreaming.postMessage('<Shutdown/>');
        }
      }
    }
  }

  useEffect(() => {
    if (muteAudio) {
      console.log('[ Init media capture ]')
      InitCapture();
    }
    else {
      console.log('[ Stop media capture ]')
      StopCapture();
    }

  }, [muteAudio]);





  useEffect(() => {
    const modelPanel = modelPanelRef.current
    if (!modelPanel) return

    const resizeObserver = new ResizeObserver(([entry]) => {
      setModelPanelHeight(entry.contentRect.height);
    })
    resizeObserver.observe(modelPanel)

    return () => resizeObserver.disconnect()
  }, [authReady])


  useEffect(() => {
    if (saveDocument) {

      document.fonts.load('12px "Tiny5 Duo"').then(() => {
        document.fonts.ready.then(() => {
          const sanitisedText: string = sanitizePlainText(transcription.current);

          const pdf = new jsPDF();
          const margin = 15;
          const pageWidth = pdf.internal.pageSize.getWidth();
          const pageHeight = pdf.internal.pageSize.getHeight();
          const lineHeight = 7; // mm; adjust for your font size

          pdf.setFontSize(16);
          pdf.setTextColor(248, 248, 248); // text color

          pdf.setFont('Tiny5-Duo', 'normal');

          const lines = pdf.splitTextToSize(
            sanitisedText,
            pageWidth - margin * 2,
          );

          const paintBackground = () => {
            pdf.setFillColor(0, 59, 95); // background color
            pdf.rect(0, 0, pageWidth, pageHeight, 'F');
          };

          paintBackground();

          let y = margin;

          for (const line of lines) {
            if (y + lineHeight > pageHeight - margin) {
              pdf.addPage();
              paintBackground();
              y = margin;
            }

            pdf.text(line, margin, y);
            y += lineHeight;
          }
          
          pdf.save('pyctate-transcription.pdf');
          setSaveDocument(false);
        });
      });
    }
  }, [saveDocument])

  useEffect(() => {
    if (clearTranscription) {
      transcription.current = '';
      setTranscriptionValue('')
      setClearTranscription(false);
    }
  }, [clearTranscription])

  useEffect(() => {
    if (currentModel != model.current) {
      model.current = currentModel;
    }
  }, [currentModel])

  useEffect(() => {
    if (currentPrecision != precision.current) {
      precision.current = currentPrecision;
    }
  }, [currentPrecision])

  if (!authReady) return null

  return (
    <RootPanel style={{ backgroundColor: '#2b4a6d', display: 'flex', flexDirection: 'column' }}>
      <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:ital,wght@0,100..700;1,100..700&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Micro+5&family=Tiny5+Duo:ital,wght@0,100..900;1,100..900&display=swap');
      </style>
      <CustomAppBar
        logoWidth="50px"
        logoHeight="50px"
        appBarTextColor="#003b5f"
        appBarColor="#f8f8f8"
        appBarSecondaryTextColor="#0989d3"
        authButtonTextColor="#003b5f"
        routesInfo={[
          ['/', 'Transcription'],
          ['/about', 'About'],
          ['/auth', '[auth]'],
        ]}
        zIndex={expandTranscriptionPanel ? -1 : undefined}
      />

      <DeviceSelector desktopChildren={
        <div style={{ display: 'grid', placeItems: 'center', width: '100%', minHeight: 'calc(100vh - 64px)', padding: '10px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(500px, 100%), 1fr))', gap: '10px', width: 'calc(100% - 20px)', height: 'fit-content', minWidth: 0 }}>
            <div ref={modelPanelRef} style={{ display: 'block', width: '100%', height: 'fit-content', minWidth: 0 }}>
              <CustomPaper background_color='#f8f8f8' width='100%' minWidth='0' height='fit-content' boxShadow='1px 0px 10px #54b9f3'>
                <div style={{ textAlign: 'start' }}>
                  <Typography sx={{ marginTop: '10px', marginLeft: '10px', color: '#003b5f', fontFamily: 'Roboto Mono, monospace', marginBottom: '40px', fontWeight: '800' }} variant='h5'>
                    // Ready to transcribe.
                  </Typography>
                </div>
                <Divider sx={{
                  margin: '20px 0px 20px 0px',
                  borderColor: '#003b5f',
                  borderWidth: '1.2px'
                }} />
                <div style={{ textAlign: 'start' }}>
                  <Typography sx={{ marginLeft: '10px', color: '#003b5f', fontFamily: 'Roboto Mono, monospace', marginBottom: '10px' }} variant='h6'>
                    // Select STT Model
                  </Typography>
                  <CustomSelectionField label='Model' size='medium' minWidth='80%' menuBackgroundColor='#eeebeb' textColor='#003b5f' borderColor='#003b5f' menuContents={['Nemo CTC Critinet 512', 'Nemo CTC Conformer Large', 'Nemo Parakeet TDT-CTC 110M']} enabled={modelSelectionEnabled} onChange={setCurrentModel} />
                </div>
                <Divider sx={{
                  margin: '20px 0px 20px 0px',
                  borderColor: '#003b5f',
                }} />
                <div style={{ textAlign: 'start' }}>
                  <Typography sx={{ marginLeft: '10px', color: '#003b5f', fontFamily: 'Roboto Mono, monospace', marginBottom: '10px' }} variant='h6'>
                    // Select model precision
                  </Typography>
                  <CustomSelectionField label='Model Precision' minWidth='40%' menuBackgroundColor='#eeebeb' textColor='#003b5f' borderColor='#003b5f' menuContents={currentModel === 'Nemo Parakeet TDT-CTC 110M' ? ['Quantised 8'] : ['Quantised 8', 'Full-Precision 32']} enabled={precisionSelectionEnabled} onChange={setCurrentPrecision} />
                </div>
                <Divider sx={{
                  margin: '20px 0px 20px 0px',
                  borderColor: '#003b5f',
                }} />
                <div style={{ height: '50px', display: 'grid', gridTemplateColumns: 'minmax(0, 1.8fr) minmax(0, 0.3fr)', minWidth: 0, overflow: 'hidden', borderRadius: '12px', borderColor: '#003b5f', borderWidth: '0.5px', borderStyle: 'solid' }}>
                  <div style={{ display: 'flex', flexDirection: 'row', minWidth: 0, overflow: 'hidden' }}>
                    <div style={{ display: 'flex', flex: '1 1 0', flexDirection: 'row', width: 0, height: '100%', minWidth: 0, overflow: 'hidden', background: 'linear-gradient(to left top, #00558a, #003b5f)', borderRadius: '10px 0px 0px 10px', borderColor: '#003b5f', borderWidth: '0px' }}>

                      <div id='waveform' style={{
                        alignSelf: 'center',
                        flex: '1 1 0',
                        minWidth: 0,
                        maxWidth: '100%',
                        height: '100%',
                        margin: '5px 0',
                        overflow: 'hidden',
                      }}>
                        {
                          muteAudio ? <LiveWaveformVisualiser stream={audioStream} /> : <div />
                        }
                      </div>

                    </div>
                    <div style={{ height: '100%', width: '1px', backgroundColor: '#003b5f' }} />
                  </div>
                  <div style={{ textAlign: 'center', display: 'flex', justifyContent: 'center', flexDirection: 'column', background: 'linear-gradient(to left top, #dadada, #aaa7a7)', borderRadius: '0px 10px 10px 0px' }}>
                    <IconButton aria-label="Microphone off" color="primary" onClick={() => { setMuteAudio(!muteAudio) }} sx={{
                      alignSelf: 'center'
                    }}>
                      {
                        muteAudio ? <MicOffIcon /> : <MicIcon />
                      }
                    </IconButton>
                  </div>
                </div>
              </CustomPaper>
            </div>

            <div style={{ display: 'block', width: '100%', height: modelPanelHeight ? `${modelPanelHeight}px` : 'fit-content' }}>
              <CustomPaper position={expandTranscriptionPanel ? 'absolute' : 'relative'} top={expandTranscriptionPanel ? '0' : 'default'} left={expandTranscriptionPanel ? '0' : 'default'} zIndex={expandTranscriptionPanel ? 100 : 0} background_color='#f8f8f8' boxShadow='1px 0px 10px #54b9f3' width={expandTranscriptionPanel ? '100vw' : '100%'} height={expandTranscriptionPanel ? '100vh' : '100%'} padding='6px'>
                <div style={{ display: 'flex', borderRadius: '3px', textAlign: 'start', backgroundColor: '#f8f8f8', flexDirection: 'column', boxSizing: 'border-box', width: '100%', height: '100%', minWidth: 0, minHeight: 0 }}>
                  <div style={{ display: 'grid', backgroundColor: '#f8f8f8', gridTemplateColumns: '1.8fr 0.2fr', width: '100%', justifyContent: 'center', height: '40px' }}>
                    <div style={{ display: 'gird', gridTemplateColumns: '1fr 1fr', width: '100%', height: '100%', borderRadius: '10px' }} >
                      <div style={{ display: 'flex', flexDirection: 'row', justifyContent: 'start', width: '100%', height: '100%', borderRadius: '10px' }}>

                        <IconButton aria-label="Clear Transcription" color="primary" sx={{
                          height: 'fit-content',
                          alignSelf: 'center',
                          color: '#003b5f',
                          marginRight: '20px'
                        }} onClick={() => { setClearTranscription(true) }} >
                          <RestartAltIcon sx={{
                            height: '20px',
                            width: '20px'
                          }} />
                        </IconButton>

                        <IconButton aria-label="Save transcription" color="primary" sx={{
                          height: 'fit-content',
                          alignSelf: 'center',
                          color: '#003b5f'
                        }} onClick={() => { setSaveDocument(true) }} >
                          <SaveIcon sx={{
                            height: '20px',
                            width: '20px'
                          }} />
                        </IconButton>

                      </div>
                      <div />
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'row', justifyContent: 'end', width: '100%', height: '100%', borderRadius: '10px' }}>
                      <IconButton aria-label="Expand off" color="primary" sx={{
                        height: 'fit-content',
                        alignSelf: 'center',
                        color: '#003b5f'
                      }} onClick={() => { setExpandTranscriptionPanel(!expandTranscriptionPanel) }} >
                        {
                          expandTranscriptionPanel ?
                            <CloseFullscreen sx={{
                              height: '20px',
                              width: '20px'
                            }} /> :
                            <OpenInFull sx={{
                              height: '20px',
                              width: '20px'
                            }} />
                        }
                      </IconButton>
                    </div>
                  </div>
                  <div style={{ display: 'flex', borderRadius: '3px', textAlign: 'start', backgroundColor: '#003b5f', flexDirection: 'column', boxSizing: 'border-box', width: '100%', height: '100%', minWidth: 0, minHeight: 0, overflow: 'hidden', borderColor: '#afafaf', borderWidth: '2px' }}>
                    <Typography sx={{ margin: '10px', color: '#f8f8f8', fontFamily: '"Tiny5 Duo", sans-serif;', fontSize: '15px' }}>
                      {initLabel}
                    </Typography>

                    <Divider sx={{
                      margin: '0px 10px 0px 10px',
                      borderColor: '#f8f8f8',
                    }} />

                    <CodeMirror
                      id='transcription_container'
                      readOnly={true}
                      aria-label="Transcription"
                      value={transcriptionValue}
                      extensions={transcriptionEditorExtensions}
                      basicSetup={{
                        lineNumbers: false,
                        foldGutter: false,
                        highlightActiveLine: false,
                        highlightActiveLineGutter: false,
                      }}
                      theme="none"
                      height="100%"
                      maxHeight="100%"
                      style={{
                        width: '100%',
                        height: '100%',
                        minWidth: 0,
                        minHeight: 0,
                        flex: '1 1 0',
                        marginTop: '10px',
                        marginBottom: '10px',
                        borderRadius: '3px',
                        overflow: 'hidden',
                      }}
                    />
                  </div>
                </div>
              </CustomPaper>
            </div>
          </div>
        </div>}
        mobileChildren={
          <div>
            Mobile Content
          </div>} />
    </RootPanel>
  )
}

import { useEffect, useRef, useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { getIfUserLoggedIn, logoutAccount } from '../firebase/firebase_auth'
import RootPanel from '#/components/RootPanel'
import CustomAppBar from '#/components/CustomAppBar'
import DeviceSelector from '#/components/DeviceSelector'
import CustomPaper from '#/components/CustomPaper'
import CustomSelectionField from '#/components/CustomSelectionField'
import Typography from '@mui/material/Typography'
import Divider from '@mui/material/Divider'
import IconButton from '@mui/material/IconButton'
import CircularProgress from '@mui/material/CircularProgress'
import MicOffIcon from '@mui/icons-material/MicOff'
import MicIcon from '@mui/icons-material/Mic'
import SettingsIcon from '@mui/icons-material/Settings'
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
import NotificationSystem from "../components/NotificationSystem.js"
import { getAvailableServer } from '#/firebase/firebase_database.js'


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

  const [expandTranscriptionPanel, setExpandTranscriptionPanel] = useState<boolean>(false);
  const [expandedTranscriptionPanelTopAndLeft, setExpandedTranscriptionPanelTopAndLeft] = useState<string | undefined>('15%');
  const expandedTranscriptionPanelTopAndLeftRef = useRef<number>(15);
  const transcriptionExpansionAnimationInterval = useRef<NodeJS.Timeout | undefined>(undefined);

  useEffect(() => {
    if (!expandTranscriptionPanel) {
      setExpandedTranscriptionPanelTopAndLeft('15%');
      expandedTranscriptionPanelTopAndLeftRef.current = 15;
      clearInterval(transcriptionExpansionAnimationInterval.current);
    }
    else {
      transcriptionExpansionAnimationInterval.current = setInterval(initTranscriptionPanelExpansionAnimation, 1);
    }
  }, [expandTranscriptionPanel]);

  const [hydrated, setHydrated] = useState<boolean>(false);

  const flickerAnimationInterval = useRef<NodeJS.Timeout | undefined>(undefined);
  const flickerPercent = useRef<number>(90);
  const switchFlickerOffset = useRef<boolean>(false);
  const [linearGradient, setLinearGradient] = useState<string>('linear-gradient(0deg, #2b4a6d 10%, #6d95c4 90%, #2b4a6d 100%)');


  const initLabelValue = useRef<string>(targetInitMarker);
  const markerIndex = useRef<number>(0);
  const [initLabel, setInitLabel] = useState<string>(targetInitMarker);
  const markerAnimationInterval = useRef<NodeJS.Timeout | undefined>(undefined);

  const [webSocketStreaming, setWebSocketStreaming] = useState<Worker | undefined>(undefined);
  const webSocketStreamingRef = useRef<Worker | undefined>(undefined);

  const shutdownRequestedRef = useRef(false);
  const streamingFailureHandledRef = useRef(false);
  const webWorkerInit = useRef<boolean>(false);

  const jwtValidatationProcedureInitiated = useRef<boolean>(false);
  const jwtValidated = useRef<boolean>(false);

  const modelParamatersValidatationProcedureInitiated = useRef<boolean>(false);
  const modelParamatersValidated = useRef<boolean>(false);

  const [authReady, setAuthReady] = useState<boolean>(false);
  const [muteAudio, setMuteAudio] = useState<boolean>(false);
  const [messageExchangePending, setMessageExchangePending] = useState<boolean>(false);
  const [mobileSettingsOpen, setMobileSettingsOpen] = useState<boolean>(false);
  const [audioStream, setAudioStream] = useState<MediaStream | null>(null);
  const [modelPanelHeight, setModelPanelHeight] = useState<number>();
  const modelPanelRef = useRef<HTMLDivElement>(null);


  const model = useRef<string>('');
  const precision = useRef<string>('');

  const [currentModel, setCurrentModel] = useState<string>('');
  const [currentPrecision, setCurrentPrecision] = useState<string>('');

  const [modelSelectionEnabled, setModelSelectionEnabled] = useState(true);
  const [precisionSelectionEnabled, setPrecisionSelectionEnabled] = useState(true);


  const [notificationText, setNotificationText] = useState('');
  const [notificationType, setNotificationType] = useState<'success' | 'error' | 'warning' | 'info'>('info');
  const [notificationOpen, setNotificationOpen] = useState(false);


  const transcription = useRef<string>('');
  const [transcriptionValue, setTranscriptionValue] = useState<string>('');

  const [saveDocument, setSaveDocument] = useState<boolean>();
  const [clearTranscription, setClearTranscription] = useState<boolean>();


  async function notificationCloseCallback() {
    if (notificationType === 'error' &&
      (notificationText === 'Invalid log in session.' ||
        notificationText === 'Log in session expired.' ||
        notificationText === 'Log in session revoked.')) {

      logoutAccount();
      window.location.href = '/auth';
    }
  }

  function StreamAudioToServer(bytes: ArrayBuffer) {
    if (jwtValidated.current && modelParamatersValidated.current) {
      webSocketStreamingRef.current?.postMessage(bytes);
    }
  }

  function handleStreamingFailure(message: string) {
    if (streamingFailureHandledRef.current) {
      return;
    }

    streamingFailureHandledRef.current = true;
    setMessageExchangePending(false);
    setNotificationType('error');
    setNotificationText(message);
    setNotificationOpen(true);
    void StopCapture();
  }

  function initTranscriptionPanelExpansionAnimation() {
    if (expandedTranscriptionPanelTopAndLeftRef.current > 0) {
      --expandedTranscriptionPanelTopAndLeftRef.current;
      setExpandedTranscriptionPanelTopAndLeft(`${expandedTranscriptionPanelTopAndLeftRef.current}%`);
    }
    else {
      clearInterval(transcriptionExpansionAnimationInterval.current);
      transcriptionExpansionAnimationInterval.current = undefined;
    }
  }


  function initFlickerAnimation() {
    if (!switchFlickerOffset.current) {
      if (flickerPercent.current < 30) {
        switchFlickerOffset.current = true;
      }
      else {
        flickerPercent.current = flickerPercent.current - 1;
      }
    }
    else {
      if (flickerPercent.current > 90) {
        switchFlickerOffset.current = false;
      }
      else {
        flickerPercent.current = flickerPercent.current + 1;
      }
    }


    setLinearGradient(`linear-gradient(0deg, #2b4a6d 10%, #19232e ${flickerPercent.current}%, #2b4a6d 100%)`);
  }


  function initAnimation() {
    if (markerIndex.current < targetInitLabel.length) {
      initLabelValue.current += targetInitLabel[markerIndex.current];
      setInitLabel(initLabelValue.current);
      markerIndex.current++;
    }
    else {
      clearInterval(markerAnimationInterval.current);
    }
  }


  function sanitizePlainText(value: string): string {
    return value
      .normalize('NFC')
      .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, '')
      .trim();
  }

  function isSymbol(char: string): boolean {
    // Treat punctuation as terminal characters too. `\p{S}` only matches
    // Unicode symbols and misses `.`, `!`, `?`, quotes, and other punctuation.
    return /^[\p{P}\p{S}]$/u.test(char);
  }


  useEffect(() => {
    getIfUserLoggedIn().then((isUserLoggedIn) => {
      if (isUserLoggedIn) {
        setAuthReady(true);
      } else {
        window.location.href = '/auth'
      }
    });
  }, []);


  useEffect(() => {
    if (!hydrated) {
      markerAnimationInterval.current ?? clearInterval(markerAnimationInterval.current);
      markerAnimationInterval.current = setInterval(initAnimation, 100);

      flickerAnimationInterval.current ?? clearInterval(flickerAnimationInterval.current);
      flickerAnimationInterval.current = setInterval(initFlickerAnimation, 50);

      setHydrated(true);
    }
  }, [hydrated])



  useEffect(() => {
    if (webSocketStreaming) {
      webSocketStreaming.onmessage = (event: MessageEvent) => {
        const [isStatus, payload] = event.data;
        console.log(payload);
        if (isStatus) {


          if (shutdownRequestedRef.current && String(payload).startsWith('[ Socket closed:')) {
            shutdownRequestedRef.current = false;
            webSocketStreaming.terminate();
            setWebSocketStreaming(undefined);
            webSocketStreamingRef.current = undefined;
            return;
          }


          const statusMessage = String(payload);

          if (statusMessage.includes('[ WebSocket error:') ||
            statusMessage.includes('[ WebSocket setup error:') ||
            statusMessage.includes('[ WebSocket send error:') ||
            statusMessage.includes('[ WebSocket not initialized;') ||
            statusMessage.includes('[ WebSocket is still connecting;')) {
            handleStreamingFailure('Unable to communicate with the server.');
          }

          if (statusMessage.startsWith('[ Socket closed:') && !shutdownRequestedRef.current) {
            handleStreamingFailure('The connection to the server was closed.');
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
                  setMessageExchangePending(false);
                  setNotificationType('error');
                  setNotificationText('Authentication session invalid');
                  setNotificationOpen(true);
                  StopCapture();
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
            else {
              switch (payload) {
                case "<JWT_Invalid/>":
                  setMessageExchangePending(false);
                  setNotificationType('error');
                  setNotificationText('Invalid log in session.');
                  setNotificationOpen(true);
                  StopCapture();
                  break;

                case "<JWT_Token_Expired/>":
                  setMessageExchangePending(false);
                  setNotificationType('error');
                  setNotificationText('Log in session expired.');
                  setNotificationOpen(true);
                  StopCapture();
                  break;

                case "<JWT_Token_Revoked/>":
                  setMessageExchangePending(false);
                  setNotificationType('error');
                  setNotificationText('Log in session revoked.');
                  setNotificationOpen(true);
                  StopCapture();
                  break;

                case "<Invalid_Account/>":
                  setMessageExchangePending(false);
                  setNotificationType('error');
                  setNotificationText('Invalid user account.');
                  setNotificationOpen(true);
                  StopCapture();
                  break;

                case "<Invalid_Message/>":
                  setMessageExchangePending(false);
                  setNotificationType('error');
                  setNotificationText('Invalid message format.');
                  setNotificationOpen(true);
                  StopCapture();
                  break

                case "<Internal_Server_Error/>":
                  setMessageExchangePending(false);
                  setNotificationType('error');
                  setNotificationText('Internal server error.');
                  setNotificationOpen(true);
                  StopCapture();
                  break;
              }
            }
          }
          else {
            if (!modelParamatersValidated.current) {

              if (payload === '<Valid_Model_Parameters/>') {
                modelParamatersValidated.current = true;
                setMessageExchangePending(false);
              }
              else if (payload === '<Invalid_Model_Parameters/>') {
                setMessageExchangePending(false);
                setNotificationType('error');
                setNotificationText('Invalid model name or model precision.');
                setNotificationOpen(true);
                StopCapture();
              }
            }
            else {
              const _message = String(payload).trim();

              if (_message !== '') {
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
        handleStreamingFailure('The streaming connection failed.');
        shutdownRequestedRef.current = true;
        webSocketStreaming.terminate();
        setWebSocketStreaming(undefined);
        webSocketStreamingRef.current = undefined;
      };
    }


    if (!webWorkerInit.current && webSocketStreaming) {
      shutdownRequestedRef.current = false;

      getAvailableServer().then((result) => {
        if (result.isSucessful) {
          const [address, protocol] = result.payload;

          console.log("address: " + address)
          console.log("protocol: " + protocol)

          webSocketStreaming?.postMessage([address, protocol]);
          webSocketStreamingRef.current = webSocketStreaming;
        }
        else {
          handleStreamingFailure('Unable to find an available server.');
        }
      }).catch((error) => {
        console.error('Unable to find an available server:', error);
        handleStreamingFailure('Unable to find an available server.');
      });
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
    streamingFailureHandledRef.current = false;
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
      else {
        setMessageExchangePending(false);
        setNotificationType('error');
        setNotificationText(message || 'Unable to start audio capture.');
        setNotificationOpen(true);
        setMuteAudio(false);
      }

    });
  }

  async function StopCapture() {
    const [message, isSuccessful]: [string, boolean] = StopAudioCapture();
    console.log('StopCapture message:', message);
    console.log('StopCapture status:', isSuccessful);

    if (isSuccessful) {
      setMessageExchangePending(false);
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
    else {
      setMessageExchangePending(false);
      setMuteAudio(false);
      setModelSelectionEnabled(true);
      setPrecisionSelectionEnabled(true);
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
    <RootPanel style={{ background: linearGradient, display: 'flex', flexDirection: 'column' }}>
      <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:ital,wght@0,100..700;1,100..700&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Micro+5&family=Tiny5+Duo:ital,wght@0,100..900;1,100..900&display=swap');
      </style>

      {notificationOpen && (
        <NotificationSystem
          notificationText={notificationText}
          notificationType={notificationType}
          openState={notificationOpen}
          setOpenState={setNotificationOpen}
          onCloseCallback={notificationCloseCallback}
        />
      )}
      <CustomAppBar
        logoWidth="50px"
        logoHeight="50px"
        appBarTextColor="#003b5f"
        appBarColor="#f8f8f8"
        appBarSecondaryTextColor="#0a70ac"
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
                  <CustomSelectionField label='Model Precision' minWidth='40%' menuBackgroundColor='#eeebeb' textColor='#003b5f' borderColor='#003b5f' menuContents={currentModel === 'Nemo Parakeet TDT-CTC 110M' ? ['Quantised 8'] : ['Quantised 8', 'Floating-Point 32']} enabled={precisionSelectionEnabled} onChange={setCurrentPrecision} />
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
                    <IconButton aria-label="Microphone off" color="primary" onClick={() => {
                      const nextMuteAudio = !muteAudio;
                      setMessageExchangePending(nextMuteAudio);
                      setMuteAudio(nextMuteAudio);
                    }} sx={{
                      alignSelf: 'center'
                    }}>
                      {
                        messageExchangePending
                          ? <CircularProgress size={24} />
                          : muteAudio ? <MicOffIcon /> : <MicIcon />
                      }
                    </IconButton>
                  </div>
                </div>
              </CustomPaper>
            </div>

            <div style={{ display: 'block', width: '100%', height: modelPanelHeight ? `${modelPanelHeight}px` : 'fit-content' }}>
              <CustomPaper position={expandTranscriptionPanel ? 'absolute' : 'relative'} top={expandTranscriptionPanel ? expandedTranscriptionPanelTopAndLeft : 'default'} left={expandTranscriptionPanel ? expandedTranscriptionPanelTopAndLeft : 'default'} zIndex={expandTranscriptionPanel ? 1 : 0} background_color='#f8f8f8' boxShadow='1px 0px 10px #54b9f3' width={expandTranscriptionPanel ? '100vw' : '100%'} height={expandTranscriptionPanel ? '100vh' : '100%'} padding='6px'>
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
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', width: '100%', minHeight: 'calc(100dvh - 128px)', boxSizing: 'border-box', padding: '12px' }}>
            <div style={{ display: 'flex', flexDirection:'row', justifyContent:'end', alignItems: 'center', minHeight: '44px' }}>
              <IconButton aria-label={mobileSettingsOpen ? 'Close model settings' : 'Open model settings'} color='primary' onClick={() => { setMobileSettingsOpen(!mobileSettingsOpen) }} sx={{ color: '#38a3e0', minWidth: '44px', minHeight: '44px' }}>
                <SettingsIcon />
              </IconButton>
            </div>

            {mobileSettingsOpen && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '12px', borderRadius: '12px', backgroundColor: '#003b5f', textAlign: 'left', boxShadow: '1px 0px 10px #54b9f3',}}>
                <CustomSelectionField label='Model' size='small' minWidth='80%' menuBackgroundColor='#003b5f' textColor='#78bee7' borderColor='#0876b5' menuContents={['Nemo CTC Critinet 512', 'Nemo CTC Conformer Large', 'Nemo Parakeet TDT-CTC 110M']} enabled={modelSelectionEnabled} onChange={setCurrentModel} />
                <CustomSelectionField label='Model Precision' size='small' minWidth='80%' menuBackgroundColor='#003b5f' textColor='#78bee7' borderColor='#0876b5' menuContents={currentModel === 'Nemo Parakeet TDT-CTC 110M' ? ['Quantised 8'] : ['Quantised 8', 'Floating-Point 32']} enabled={precisionSelectionEnabled} onChange={setCurrentPrecision} />
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', flex: '1 1 auto', minHeight: 'min(52vh, 420px)', minWidth: 0, overflow: 'hidden', borderRadius: '16px', backgroundColor: '#003b5f', boxShadow: '1px 0px 10px #54b9f3', textAlign: 'left' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', padding: '12px 12px 8px' }}>
                <div/>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: muteAudio ? '#9be3b0' : '#c3d7e3', fontFamily: 'Roboto Mono, monospace', fontSize: '0.7rem' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: messageExchangePending ? '#55c779' : '#8ca8b7' }} />
                  {messageExchangePending ? 'LIVE' : 'READY'}
                </div>
              </div>
              <Divider sx={{ margin: '0 12px', borderColor: '#f8f8f8', opacity: 0.45 }} />
              <Typography sx={{ margin: '10px 12px 0', color: '#d7e8f1', fontFamily: '"Tiny5 Duo", sans-serif', fontSize: '15px' }}>
                {initLabel}
              </Typography>
              <CodeMirror
                id='transcription_container'
                readOnly={true}
                aria-label='Transcription'
                value={transcriptionValue}
                extensions={transcriptionEditorExtensions}
                basicSetup={{ lineNumbers: false, foldGutter: false, highlightActiveLine: false, highlightActiveLineGutter: false }}
                theme='none'
                height='100%'
                maxHeight='100%'
                style={{ width: '100%', height: '100%', minWidth: 0, minHeight: 0, flex: '1 1 0', marginTop: '8px', marginBottom: '8px', overflow: 'hidden' }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minHeight: '64px' }}>
              <IconButton aria-label={muteAudio ? 'Stop microphone' : 'Start microphone'} color='primary' onClick={() => {
                const nextMuteAudio = !muteAudio;
                setMessageExchangePending(nextMuteAudio);
                setMuteAudio(nextMuteAudio);
              }} sx={{ width: '56px', height: '56px', flex: '0 0 56px', color: '#fff', backgroundColor: '#0989d3', '&:hover': { backgroundColor: '#0876b5' } }}>
                {messageExchangePending ? <CircularProgress size={24} sx={{ color: '#fff' }} /> : muteAudio ? <MicOffIcon /> : <MicIcon />}
              </IconButton>
              <div style={{ display: 'flex', alignItems: 'center', flex: '1 1 auto', minWidth: 0, height: '48px', overflow: 'hidden', padding: '0 8px', borderRadius: '12px', background: 'linear-gradient(to left top, #00558a, #003b5f)' }}>
                {muteAudio ? <LiveWaveformVisualiser stream={audioStream} /> : <Typography sx={{ color: '#d7e8f1', fontSize: '0.8rem' }}>Tap the mic to begin</Typography>}
              </div>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <IconButton aria-label='Clear transcription' color='primary' onClick={() => { setClearTranscription(true) }} sx={{ color: '#38a3e0', minWidth: '44px', minHeight: '44px' }}>
                  <RestartAltIcon />
                </IconButton>
                <IconButton aria-label='Save transcription' color='primary' onClick={() => { setSaveDocument(true) }} sx={{ color: '#38a3e0', minWidth: '44px', minHeight: '44px' }}>
                  <SaveIcon />
                </IconButton>
              </div>
            </div>
          </div>} />
    </RootPanel>
  )
}

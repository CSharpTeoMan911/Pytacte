import { useEffect, useRef, useState } from 'react'
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
import CropSquare from '@mui/icons-material/CropSquare'
import FilterNone  from '@mui/icons-material/FilterNone'
import LiveWaveformRecorder from '#/components/LiveWaveformRecorder'
import CodeMirror from '@uiw/react-codemirror'
import { EditorView } from '@codemirror/view'

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
  const targetInitLabel = ' init pyctate';

  const [initLabel, setInitLabel] = useState<string>(targetInitMarker);
  const [hydrated, setHydrated] = useState<boolean>(false);
  let markerAnimationInterval: NodeJS.Timeout | undefined;
  let initLabelValue: string = targetInitMarker;
  let markerIndex: number = 0;

  const [authReady, setAuthReady] = useState<boolean>(false)
  const [muteAudio, setMuteAudio] = useState<boolean>(false);
  const [modelPanelHeight, setModelPanelHeight] = useState<number>()
  const modelPanelRef = useRef<HTMLDivElement>(null)

  let text = `Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.\nUt enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.\nExcepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

Curabitur pretium tincidunt lacus. Nulla gravida orci a odio.\nNullam varius, turpis et commodo pharetra, est eros bibendum elit, nec luctus magna felis sollicitudin mauris.\nInteger in mauris eu nibh euismod gravida.

Phasellus fermentum in, dolor. Pellentesque facilisis. Nulla imperdiet sit amet magna.\nVestibulum dapibus, mauris nec malesuada fames ac turpis velit, rhoncus eu, luctus et interdum adipiscing wisi.\nAliquam erat volutpat. Donec sit amet nisl.\nAliquam semper ipsum sit amet velit. Sed eu leo.\n`

  text = `${text}\n${text}\n${text}\n${text}`


  const [transcription, setTranscription] = useState(text)

  console.log(`muteAudio: ${muteAudio}`)


  function initAnimation() {
    console.log(initLabelValue);
    if (markerIndex < targetInitLabel.length) {
      initLabelValue += targetInitLabel[markerIndex];
      setInitLabel(initLabelValue);
      markerIndex++;
    }
    else {
      clearInterval(markerAnimationInterval);
    }
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
    })
  }, [])

  useEffect(() => {
    const modelPanel = modelPanelRef.current
    if (!modelPanel) return

    const resizeObserver = new ResizeObserver(([entry]) => {
      setModelPanelHeight(entry.contentRect.height)
    })
    resizeObserver.observe(modelPanel)

    return () => resizeObserver.disconnect()
  }, [authReady])

  if (!authReady) return null

  return (
    <RootPanel style={{ backgroundColor: '#c9c9c9', display: 'flex', flexDirection: 'column' }}>
      <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:ital,wght@0,100..700;1,100..700&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Micro+5&family=Tiny5+Duo:ital,wght@0,100..900;1,100..900&display=swap');
      </style>


      <CustomAppBar
        logoWidth="50px"
        logoHeight="50px"
        appBarTextColor="#003b5f"
        appBarColor="#f8f8f8"
        appBarSecondaryTextColor="#0961d3"
        authButtonTextColor="#003b5f"
        routesInfo={[
          ['/', 'Transcription'],
          ['/about', 'About'],
          ['/auth', '[auth]'],
        ]} />

      <DeviceSelector desktopChildren={
        <div style={{ display: 'grid', placeItems: 'center', width: '100%', minHeight: 'calc(100vh - 64px)', padding: '10px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(500px, 100%), 1fr))', gap: '10px', width: 'calc(100% - 20px)', height: 'fit-content' }}>
            <div ref={modelPanelRef} style={{ display: 'block', width: '100%', height: 'fit-content' }}>
              <CustomPaper background_color='#f8f8f8' width='100%' height='fit-content' boxShadow='1px 0px 10px #004faa'>
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
                  <CustomSelectionField label='Model' size='medium' minWidth='80%' menuBackgroundColor='#eeebeb' textColor='#003b5f' borderColor='#003b5f' menuContents={['Moonshine Streaming Medium', 'Granite Speech 5.0 TurboCTC', 'Parakeet TDT-CTC 110M']} />
                </div>
                <Divider sx={{
                  margin: '20px 0px 20px 0px',
                  borderColor: '#003b5f',
                }} />
                <div style={{ textAlign: 'start' }}>
                  <Typography sx={{ marginLeft: '10px', color: '#003b5f', fontFamily: 'Roboto Mono, monospace', marginBottom: '10px' }} variant='h6'>
                    // Select model precision
                  </Typography>
                  <CustomSelectionField label='Model Precision' minWidth='40%' menuBackgroundColor='#272525' textColor='#003b5f' borderColor='#003b5f' menuContents={['Quantised 8', 'Full-Precision 16']} />
                </div>
                <Divider sx={{
                  margin: '20px 0px 20px 0px',
                  borderColor: '#003b5f',
                }} />
                <div style={{ height: '50px', display: 'grid', gridTemplateColumns: '1.8fr 0.3fr', borderRadius: '12px', borderColor: '#003b5f', borderWidth: '0.5px', borderStyle: 'solid' }}>
                  <div style={{ display: 'flex', flexDirection: 'row' }}>
                    <div style={{ width: '100%', height: '100%', background: 'linear-gradient(to left top, #00558a, #003b5f)', borderRadius: '10px 0px 0px 10px', borderColor: '#003b5f', borderWidth: '0px' }}>

                    </div>
                    <div style={{ height: '100%', width: '1px', backgroundColor: '#003b5f' }}>

                    </div>
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
              <CustomPaper background_color='#f8f8f8' boxShadow='1px 0px 10px #004faa' width='100%' height='100%' padding='6px'>
                <div style={{ display: 'flex', borderRadius: '3px', textAlign: 'start', backgroundColor: '#f8f8f8', flexDirection: 'column', boxSizing: 'border-box', width: '100%', height: '100%', minWidth: 0, minHeight: 0 }}>
                  <div style={{ display: 'grid', backgroundColor: '#f8f8f8', gridTemplateColumns: '1.8fr 0.2fr', width: '100%', justifyContent: 'center', height: '40px' }}>
                    <div style={{ width: '100%', height: '100%', borderRadius: '10px' }} />
                    <div style={{ display:'flex', flexDirection:'column', justifyContent:'top', alignContent:'center', width: '100%', height: '100%', borderRadius: '10px' }}>
                      <IconButton aria-label="Expand off" color="primary" sx={{
                        height:'fit-content',
                        alignSelf: 'center',
                        color:'#003b5f'
                      }} onClick={() => { setMuteAudio(!muteAudio) }} >
                        <CropSquare sx={{
                          height:'20px',
                          width:'20px'
                        }}/>
                      </IconButton>
                    </div>
                  </div>
                  <div style={{ display: 'flex', borderRadius: '3px', textAlign: 'start', backgroundColor: '#003b5f', flexDirection: 'column', boxSizing: 'border-box', width: '100%', height: '100%', minWidth: 0, minHeight: 0, overflow: 'hidden', borderColor:'#afafaf', borderWidth:'2px' }}>
                    <Typography sx={{ margin: '10px', color: '#f8f8f8', fontFamily: '"Tiny5 Duo", sans-serif;', fontSize: '15px' }}>
                      {initLabel}
                    </Typography>
                    <CodeMirror
                      readOnly={true}
                      aria-label="Transcription"
                      value={transcription}
                      onChange={(value) => setTranscription(value)}
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

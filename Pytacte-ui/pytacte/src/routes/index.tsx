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
import LiveWaveformRecorder from '#/components/LiveWaveformRecorder'
import Box from '@mui/material/Box'


export const Route = createFileRoute('/')({ component: Home })

function Home() {
  const [authReady, setAuthReady] = useState(false)
  const[muteAudio, setMuteAudio] = useState(false);
  const [modelPanelHeight, setModelPanelHeight] = useState<number>()
  const modelPanelRef = useRef<HTMLDivElement>(null)

  let text = `Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.\nUt enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.\nExcepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

Curabitur pretium tincidunt lacus. Nulla gravida orci a odio.\nNullam varius, turpis et commodo pharetra, est eros bibendum elit, nec luctus magna felis sollicitudin mauris.\nInteger in mauris eu nibh euismod gravida.

Phasellus fermentum in, dolor. Pellentesque facilisis. Nulla imperdiet sit amet magna.\nVestibulum dapibus, mauris nec malesuada fames ac turpis velit, rhoncus eu, luctus et interdum adipiscing wisi.\nAliquam erat volutpat. Donec sit amet nisl.\nAliquam semper ipsum sit amet velit. Sed eu leo.\n`

  text = `${text}\n${text}\n${text}\n${text}`


  const [transcription, setTranscription] = useState(text)

  console.log(`muteAudio: ${muteAudio}`)



  useEffect(() => {
    getIfUserLoggedIn().then((isUserLoggedIn) => {
      if (isUserLoggedIn) {
        setAuthReady(true)
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
    <RootPanel style={{ backgroundColor: '#949494', display: 'flex', flexDirection: 'column' }}>
      <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:ital,wght@0,100..700;1,100..700&display=swap');
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
              <CustomPaper background_color='#464444' width='100%' height='fit-content' boxShadow='1px 0px 10px #004faa'>
                <div style={{ textAlign: 'start' }}>
                  <Typography sx={{marginTop: '10px', marginLeft: '10px', color: '#4ba2f8', fontFamily: 'Roboto Mono, monospace', marginBottom: '40px', fontWeight: '800' }} variant='h4'>
                    // Ready to transcribe.
                  </Typography>
                </div>
                <Divider sx={{
                  margin: '20px 0px 20px 0px',
                  borderColor: '#4ba2f8',
                  borderWidth: '1.2px'
                }} />
                <div style={{ textAlign: 'start' }}>
                  <Typography sx={{ marginLeft: '10px', color: '#4ba2f8', fontFamily: 'Roboto Mono, monospace', marginBottom: '10px' }} variant='h6'>
                    // Select STT Model
                  </Typography>
                  <CustomSelectionField label='Model' size='medium' minWidth='80%' menuBackgroundColor='#272525' textColor='#79bafc' borderColor='#79bafc' menuContents={['Moonshine Streaming Medium', 'Granite Speech 5.0 TurboCTC', 'Parakeet TDT-CTC 110M']} />
                </div>
                <Divider sx={{
                  margin: '20px 0px 20px 0px',
                  borderColor: '#4ba2f8',
                }} />
                <div style={{ textAlign: 'start' }}>
                  <Typography sx={{ marginLeft: '10px', color: '#4ba2f8', fontFamily: 'Roboto Mono, monospace', marginBottom: '10px' }} variant='h6'>
                    // Select model precision
                  </Typography>
                  <CustomSelectionField label='Model Precision' minWidth='40%' menuBackgroundColor='#272525' textColor='#79bafc' borderColor='#79bafc' menuContents={['Quantised 8', 'Full-Precision 16']} />
                </div>
                <Divider sx={{
                  margin: '20px 0px 20px 0px',
                  borderColor: '#4ba2f8',
                }} />
                <div style={{ height: '50px', display: 'grid', gridTemplateColumns: '1.8fr 0.3fr', borderRadius: '12px', borderColor: '#4ba2f8', borderWidth: '0.5px', borderStyle: 'solid' }}>
                  <div style={{ display: 'flex', flexDirection: 'row' }}>
                    <div style={{ width: '100%', height: '100%', background: 'linear-gradient(to left top, #131313, #424242)', borderRadius: '10px 0px 0px 10px', borderColor: '#4ba2f8', borderWidth: '0px' }}>

                    </div>
                    <div style={{ height: '100%', width: '1px', backgroundColor: '#4ba2f8' }}>

                    </div>
                  </div>
                  <div style={{ textAlign: 'center', display: 'flex', justifyContent: 'center', flexDirection: 'column', background: 'linear-gradient(to left top, #525151, #161616)', borderRadius: '0px 10px 10px 0px' }}>
                    <IconButton aria-label="Microphone off" color="primary" onClick={()=>{setMuteAudio(!muteAudio)}} sx={{
                      alignSelf:'center'
                    }}>
                      {
                        muteAudio ? <MicOffIcon/> : <MicIcon/>
                      }
                    </IconButton>
                  </div>
                </div>
              </CustomPaper>
            </div>

            <div style={{ display: 'block', width: '100%', height: modelPanelHeight ? `${modelPanelHeight}px` : 'fit-content' }}>
              <CustomPaper background_color='#464444' boxShadow='1px 0px 10px #004faa' width='100%' height='100%'>
                <div style={{ display: 'flex', flexDirection: 'column', boxSizing: 'border-box', width: '100%', height: '100%', minWidth: 0, minHeight: 0, padding: '10px', overflow: 'hidden' }}>
                  <Box
                    component="textarea"
                    aria-label="Transcription"
                    value={transcription}
                    onChange={(event) => setTranscription(event.target.value)}
                    sx={{
                      display: 'block',
                      width: '100%',
                      height: '100%',
                      maxHeight: '100%',
                      minWidth: 0,
                      minHeight: 0,
                      boxSizing: 'border-box',
                      flex: '1 1 0',
                      resize: 'none',
                      overflowX: 'hidden',
                      overflowY: 'scroll',
                      whiteSpace: 'pre-wrap',
                      overflowWrap: 'anywhere',
                      wordBreak: 'break-word',
                      border: '1px solid #4ba2f8',
                      borderRadius: '4px',
                      padding: '10px',
                      color: '#4ba2f8',
                      backgroundColor: '#272525',
                      font: 'inherit',
                      fontSize: '0.95rem',
                      lineHeight: 1.65,
                      letterSpacing: '0.01em',
                      outline: 'none',
                      boxShadow: 'inset 0 2px 8px rgba(0, 0, 0, 0.25)',
                      transition: 'border-color 160ms ease, box-shadow 160ms ease',
                      '&:focus': {
                        borderColor: '#4ba2f8',
                        boxShadow: '0 0 0 3px rgba(75, 162, 248, 0.18), inset 0 2px 8px rgba(0, 0, 0, 0.2)',
                      },
                      scrollbarWidth: 'thin',
                      scrollbarColor: '#4ba2f8 #202a35',
                      '&::-webkit-scrollbar': { width: '8px' },
                      '&::-webkit-scrollbar:horizontal': { display: 'none', height: 0 },
                      '&::-webkit-scrollbar-track': { backgroundColor: '#202a35', borderRadius: '8px' },
                      '&::-webkit-scrollbar-thumb': { backgroundColor: '#4ba2f8', borderRadius: '8px', border: '2px solid #202a35' },
                      '&::-webkit-scrollbar-thumb:hover': { backgroundColor: '#79bafc' },
                    }}
                  />
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

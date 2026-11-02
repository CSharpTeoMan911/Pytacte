import { useEffect, useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { getIfUserLoggedIn } from '../firebase/firebase_auth'
import RootPanel from '#/components/RootPanel'
import CustomAppBar from '#/components/CustomAppBar'
import DeviceSelector from '#/components/DeviceSelector'
import CustomPaper from '#/components/CustomPaper'
import CustomSelectionField from '#/components/CustomSelectionField'
import Typography from '@mui/material/Typography'
import Divider from '@mui/material/Divider'
import LiveWaveformRecorder from '#/components/LiveWaveformRecorder'


export const Route = createFileRoute('/')({ component: Home })

function Home() {
  const [authReady, setAuthReady] = useState(false)

  useEffect(() => {
    getIfUserLoggedIn().then((isUserLoggedIn) => {
      if (isUserLoggedIn) {
        setAuthReady(true)
      } else {
        window.location.href = '/auth'
      }
    })
  }, [])

  if (!authReady) return null

  return (
    <RootPanel style={{backgroundColor:'#949494', display:'flex', flexDirection:'column'}}>
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
        <div style={{ display: 'grid', placeItems: 'center', width: '100%', minHeight: 'calc(100vh - 64px)', padding:'10px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(500px, 100%), 1fr))', gap: '10px', width: 'calc(100% - 20px)', height: 'fit-content' }}>
            <div style={{ display: 'block', width: '100%', height: 'fit-content' }}>
              <CustomPaper background_color='#464444' width='100%' height='fit-content' boxShadow='1px 0px 10px #004faa'>
                <div style={{ textAlign: 'start' }}>
                  <Typography sx={{ marginLeft: '10px', color: '#4ba2f8', fontFamily: 'Roboto Mono, monospace', marginBottom: '10px' }} variant='h6'>
                    {'>'}{'>'}{'> '} Select STT Model
                  </Typography>
                  <CustomSelectionField label='Model' size='medium' minWidth='80%' menuBackgroundColor='#272525' textColor='#1085c9' borderColor='#1085c9' menuContents={['Moonshine Streaming Medium', 'Granite Speech 5.0 TurboCTC', 'Parakeet TDT-CTC 110M']} />
                </div>
                <Divider sx={{
                  margin: '20px 0px 20px 0px',
                  borderColor: '#4ba2f8',
                }} />
                <div style={{ textAlign: 'start' }}>
                  <Typography sx={{ marginLeft: '10px', color: '#4ba2f8', fontFamily: 'Roboto Mono, monospace', marginBottom: '10px' }} variant='h6'>
                    {'>'}{'>'}{'> '} Select model precision
                  </Typography>
                  <CustomSelectionField label='Model Precision' minWidth='40%' menuBackgroundColor='#272525' textColor='#1085c9' borderColor='#1085c9' menuContents={['Quantised 8', 'Full-Precision 16']} />
                </div>
                <Divider sx={{
                  margin: '20px 0px 20px 0px',
                  borderColor: '#4ba2f8',
                }} />
                <div style={{ textAlign: 'start' }}>
                  
                </div>
              </CustomPaper>
            </div>

            <div style={{ display: 'block', width: '100%', height: 'fit-content' }}>
              <CustomPaper width='100%'>
                <div></div>
                {/* <LiveWaveformRecorder onDataAvailable={(event) => {
                  // Forward each recorded audio chunk to the transcription pipeline here.
                  console.log('Audio chunk received:', event.data.size)
                }} /> */}
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

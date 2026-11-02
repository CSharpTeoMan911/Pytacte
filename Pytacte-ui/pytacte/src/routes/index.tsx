import { useEffect, useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { getIfUserLoggedIn } from '../firebase/firebase_auth'
import RootPanel from '#/components/RootPanel'
import CustomAppBar from '#/components/CustomAppBar'
import DeviceSelector from '#/components/DeviceSelector'


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
    <RootPanel>
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
        <div style={{ display: 'block', position: 'relative', width: '100%', minHeight: 'calc(100vh - 64px)'}}>
          <div style={{ display: 'block', position: 'absolute', top: '50%', left: '50%', width: 'calc(100% - 20px)', transform: 'translate(-50%, -50%)', textAlign: 'center' }}>
            <div style={{ display: 'inline-block', width: '50%', height: 'fit-content', minWidth: '500px' }}>
              Testing: (Layout 1)
            </div>

            <div style={{ display: 'inline-block', width: '50%', height: 'fit-content', minWidth: '500px' }}>
              Testing: (Layout 2)
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

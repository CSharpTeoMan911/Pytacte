import { useEffect, useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { getIfUserLoggedIn } from '../firebase/firebase_auth'


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
    <div className="p-8">
      <h1 className="text-4xl font-bold">Welcome to TanStack Start</h1>
      <p className="mt-4 text-lg">
        
      </p>
    </div>
  )
}

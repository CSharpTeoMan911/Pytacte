import { createFileRoute } from '@tanstack/react-router'
import  { getIfUserLoggedIn } from '../firebase/firebase_auth'


export const Route = createFileRoute('/')({ component: Home })

function Home() {
  if(!getIfUserLoggedIn())
    window.location.href = '/login';

  return (
    <div className="p-8">
      <h1 className="text-4xl font-bold">Welcome to TanStack Start</h1>
      <p className="mt-4 text-lg">
        
      </p>
    </div>
  )
}

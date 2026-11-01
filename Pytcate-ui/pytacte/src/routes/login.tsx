import CustomPaper from '#/components/CustomPaper'
import RootPanel from '#/components/RootPanel'
import { createFileRoute } from '@tanstack/react-router'
import DeviceSelector from '#/components/DeviceSelector'

export const Route = createFileRoute('/login')({ component: Login })

function Login() {
    return (
        <RootPanel>
            <DeviceSelector
                desktopChildren={<div>
                    
                </div>} 
                mobileChildren={<div>

                </div>} />
        </RootPanel>
    )
}
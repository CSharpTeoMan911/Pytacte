import '../styles.css'
import type { ReactNode } from 'react';


type Props = {
    children: ReactNode
    background_color?: string
}

export default function RootPanel({children, background_color}:Props){
    return (
        <div className="root_div" style={{ backgroundColor: background_color ? background_color : '#f5f5f5'}}>
            {children}
        </div>
    );
}
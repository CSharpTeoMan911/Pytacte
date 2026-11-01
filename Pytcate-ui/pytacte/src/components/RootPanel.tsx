import '../styles.css'
import type { ReactNode } from 'react';


type Props = {
    children: ReactNode
}

export default function RootPanel({children}:Props){
    return (
        <div className="root_div">
            {children}
        </div>
    );
}
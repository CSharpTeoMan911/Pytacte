import '../styles.css'
import type { CSSProperties, ReactNode } from 'react';


type Props = {
    style?: CSSProperties
    children: ReactNode
    background_color?: string
}

export default function RootPanel({ children, background_color, style }: Props) {
    if (style) {
        return (
            <div className="root_div" style={style}>
                {children}
            </div>
        );
    }
    else {
        return (
            <div className="root_div" style={{ backgroundColor: background_color ? background_color : '#f5f5f5' }}>
                {children}
            </div>
        );
    }
}
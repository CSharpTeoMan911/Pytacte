import Paper from '@mui/material/Paper';
import { styled } from '@mui/material/styles';
import type { ReactNode } from 'react';

type Props={
    children:ReactNode
    width?:string
    minWidth?:string
    height?:string
    minHeight?:string
    background_color?:string
    margin?:string
    padding?:string
}


const CustomPaperComponent = styled(Paper)<{ width?: string, height?: string,minWidth?: string, minHeight?: string, background_color?: string, margin?: string, padding?: string }>(({ theme, width, height, minWidth, minHeight, background_color, margin, padding }) => ({
  width: width || 120,
  height: height || 120,
  minWidth: minWidth || 'auto',
  minHeight: minHeight || 'auto',
  padding: padding || theme.spacing(2),
  ...theme.typography.body2,
  textAlign: 'center',
  backgroundColor: background_color === undefined ? theme.palette.background.paper : background_color,
  margin: margin || 'auto'
}));

export default function CustomPaper({children, width, height, minWidth, minHeight, background_color, margin, padding}:Props){
    return (
        <CustomPaperComponent width={width} height={height} minWidth={minWidth} minHeight={minHeight} background_color={background_color} margin={margin} padding={padding}>
            {children}
        </CustomPaperComponent>
    );
} 
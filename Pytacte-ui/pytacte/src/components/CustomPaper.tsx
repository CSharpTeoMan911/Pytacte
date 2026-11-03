import Paper from '@mui/material/Paper';
import { styled } from '@mui/material/styles';
import type { CSSProperties, ReactNode } from 'react';

type Props = {
    children: ReactNode;
    width?: string;
    minWidth?: string;
    height?: string;
    minHeight?: string;
    background_color?: string;
    margin?: string;
    padding?: string;
    boxShadow?: string;
    position?: CSSProperties['position'];
    zIndex?: number;
    top?: string;
    left?: string
};

const customProps = new Set([
    'width',
    'height',
    'minWidth',
    'minHeight',
    'background_color',
    'margin',
    'padding',
    'boxShadow',
    'position',
    'zIndex',
    'left',
    'top'
]);

const CustomPaperComponent = styled(Paper, {
    shouldForwardProp: (prop) => !customProps.has(prop as string),
})<Omit<Props, 'children'>>(
    ({ theme, width, height, minWidth, minHeight, background_color, margin, padding, boxShadow, position, zIndex, top, left }) => ({
        width: width || 120,
        height: height || 120,
        minWidth: minWidth || 'auto',
        minHeight: minHeight || 'auto',
        padding: padding || theme.spacing(2),
        ...theme.typography.body2,
        textAlign: 'center',
        backgroundColor: background_color ?? theme.palette.background.paper,
        margin: margin || 'auto',
        boxShadow: boxShadow || theme.shadows[1],
        position: position || 'relative',
        zIndex: zIndex || 0,
        top: top || 'default',
        left: left || 'default'
    }),
);

export default function CustomPaper({
    children,
    width,
    height,
    minWidth,
    minHeight,
    background_color,
    margin,
    padding,
    boxShadow,
    position,
    zIndex,
    top,
    left
}: Props) {
    return (
        <CustomPaperComponent
            width={width}
            height={height}
            minWidth={minWidth}
            minHeight={minHeight}
            background_color={background_color}
            margin={margin}
            padding={padding}
            boxShadow={boxShadow}
            position={position}
            zIndex={zIndex}
            top={top}
            left={left}
        >
            {children}
        </CustomPaperComponent>
    );
}

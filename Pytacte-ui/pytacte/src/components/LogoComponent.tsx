import Box from '@mui/material/Box';
import type { SxProps, Theme } from '@mui/material/styles';
import logo from '../images/Pyctate.png';

type Props = {
    logoSrc?: string;
    width?: number | string;
    height?: number | string;
    dynamicSizing?: boolean;
    sx?: SxProps<Theme>;
};

export default function LogoComponent({ sx, width, height, logoSrc, dynamicSizing = true }: Props) {
    return (
        <Box
            component="img"
            src={logoSrc || logo}
            alt="Pyctate"
            sx={{
                width,
                height,
                objectFit: 'contain',
                alignSelf: 'center',
                flexShrink: dynamicSizing ? 1 : 0,
                ...sx,
            }}
        />
    );
}

import Paper from '@mui/material/Paper';
import { styled } from '@mui/material/styles';
import type { ReactNode } from 'react';

type Props={
    children:ReactNode
}


const CustomPaperComponent = styled(Paper)(({ theme }) => ({
  width: 120,
  height: 120,
  padding: theme.spacing(2),
  ...theme.typography.body2,
  textAlign: 'center',
}));

export default function CustomPaper({children}:Props){
    return (
        <CustomPaperComponent>
            {children}
        </CustomPaperComponent>
    );
} 
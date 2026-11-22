import Paper from '@mui/material/Paper';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton'
import TextField from '@mui/material/TextField'
import ClosePanel from '@mui/icons-material/Close'
import textCursor from '../data/text-cursor.svg'
import googleLogo from '../data/google.png'
import mail from '../data/mail.png'
import Divider from '@mui/material/Divider'
import { useEffect, useState } from 'react';

type Props = {
    email?: string
    provider?: string
    backgroundColor: string
    secondaryColor: string
    opacity: number
    elevation: number
    zIndex?: number | string
    setOpenPanel: (open: boolean) => void
    setDeleteAccount: (open: boolean) => void
}

const accountFieldSx = {
    '& .MuiOutlinedInput-root': {
        backgroundColor: 'transparent',
        color: '#50aefc',
        fontFamily: 'Roboto Mono, monospace',
        '& fieldset, &:hover fieldset, &.Mui-focused fieldset': { border: 'none' },
    },
    '& .MuiInputBase-input': {
        fontSize: '1rem',
        fontWeight: 600,
        cursor: `url("${textCursor}") 12 12, text`,
        userSelect: 'none',
        '&::selection': { backgroundColor: 'transparent', color: 'inherit' },
    },
    '& .MuiInputLabel-root, & .MuiInputLabel-root.Mui-focused': {
        color: '#52788f',
        fontWeight: 600,
    },
}

export default function AccountsPanel({ email, provider, backgroundColor, secondaryColor, opacity, elevation, zIndex, setOpenPanel, setDeleteAccount }: Props) {

    return (<Paper elevation={elevation} sx={{
        containerName: 'account-panel',
        display: 'flex',
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100dvh',
        backgroundColor: backgroundColor,
        opacity: opacity,
        zIndex: zIndex,
        alignContent: 'center',
        justifyContent: 'center',
        borderRadius: '0px'
    }}>

        <Paper
            sx={{
                display: 'flex',
                flexDirection: 'column',
                alignSelf: 'center',
                justifySelf: 'center',
                position: 'relative',
                width: 'fit-content',
                height: 'fit-content',
                padding: '0px',
                backgroundColor: secondaryColor,
                opacity: opacity,
                zIndex: zIndex,
                borderRadius: '10px',
                overflow: 'hidden',
                boxShadow:'1px 0px 10px #00203a'
            }}>

            {/* <img className="auth-google-logo" src={googleLogo} alt="" /> */}
            <div style={{ display: 'inline-block', width: '100%', textAlign: 'end' }}>
                <IconButton aria-label="Expand off" color="primary" sx={{
                    height: 'fit-content',
                    alignSelf: 'center',
                    color: '#0081fa'
                }} onClick={() => { setOpenPanel(false); }} >
                    {
                        <ClosePanel sx={{
                            height: '25px',
                            width: '25px'
                        }} />
                    }
                </IconButton>
            </div>

            <Divider sx={{ borderColor: '#148cfc' }} />

            <div style={{ display: 'flex', flexDirection: 'column', marginTop: '10px', alignContent: 'left', gap: '16px', padding: '4px 8px 8px' }}>
                <div style={{ display: 'flex', flexDirection: 'row', width: 'fit-content' }}>
                    <TextField
                        label=''
                        value={email ?? ''}
                        variant='outlined'
                        size='small'
                        slotProps={{ htmlInput: { readOnly: true }, inputLabel: { shrink: true } }}
                        sx={{ ...accountFieldSx, width:`${String((email ? email.length - 7 : 0))}em`, maxWidth:'300px', alignSelf: 'center' }}
                    />

                    <img style={{ width: '22px', height: '22px', alignSelf: 'center', marginLeft: '5px' }} className="auth-google-logo" src={provider == 'Gmail' ? googleLogo : mail} alt="" />

                </div>
            </div>

            <Button sx={{ textTransform: 'none', color: 'rgb(0,61,110)', fontSize: '1em', fontWeight: 'bold', fontFamily: 'Roboto Mono, monospace', 
                        backgroundColor: '#50aefc', alignSelf: 'center', marginTop: '10px', borderRadius: '0px', height: '40px', paddingTop:'22px', 
                        paddingBottom:'22px'}} 
                        type="button" variant="contained" fullWidth 
                        onClick={() => { setDeleteAccount(true); }}>
                Delete Account
            </Button>

        </Paper>

    </Paper>)
}

import { useState } from 'react';
import { createFileRoute } from '@tanstack/react-router';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import InputAdornment from '@mui/material/InputAdornment';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import CustomAppBar from '#/components/CustomAppBar';
import RootPanel from '#/components/RootPanel';
import LogoComponent from '#/components/LogoComponent';
import NotificationSystem from '#/components/NotificationSystem';
import googleLogo from '../images/google.png';
import { getIfUserLoggedIn, loginAccount, loginWithGoogle, registerAccount } from '../firebase/firebase_auth';

export const Route = createFileRoute('/auth')({ component: Login });

async function handleAuthentication(isGoogleLogIn: boolean, email: string, password: string, repeatPassword: string, isRegistering: boolean, setNotificationText: (text: string) => void, setNotificationType: (type: 'success' | 'error' | 'warning' | 'info') => void, setNotificationOpen: (open: boolean) => void, setIsRegistering?: (isRegistering: boolean) => void) {
    if (isRegistering) {
        const passwordsMatch = password === repeatPassword;
        if (!passwordsMatch) {
            setNotificationText('Passwords do not match.');
            setNotificationType('error');
            setNotificationOpen(true);
            return;
        }

        const [status, message] = await registerAccount(email, password)

        if (status) {
            const registrationMessage = `${message}. Check your email to verify your account. Check your spam folder if needed.`;
            setNotificationText(registrationMessage);
            setNotificationType('success');
            setIsRegistering?.(false);
        } else {
            setNotificationText(message);
            setNotificationType('error');
        }
        setNotificationOpen(true);
    } else {
        if (isGoogleLogIn) {
            const [status, message] = await loginWithGoogle();

            if (status) {
                setNotificationText(message);
                setNotificationType('success');
            } else {
                setNotificationText(message);
                setNotificationType('error');
            }
            setNotificationOpen(true);
        }
        else {
            const [status, message] = await loginAccount(email, password);

            if (status) {
                setNotificationText(message);
                setNotificationType('success');
            } else {
                setNotificationText(message);
                setNotificationType('error');
            }
            setNotificationOpen(true);
        }
        // Implement login logic here
    }
}

async function notificationCloseCallback() {
    if (await getIfUserLoggedIn()) {
        window.location.href = '/';
    }
}


function Login() {
    const [passwordVisible, setPasswordVisible] = useState(false);
    const [isRegistering, setIsRegistering] = useState(false);

    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [repeatPassword, setRepeatPassword] = useState('');

    const [notificationText, setNotificationText] = useState('');
    const [notificationType, setNotificationType] = useState<'success' | 'error' | 'warning' | 'info'>('info');
    const [notificationOpen, setNotificationOpen] = useState(false);



    return (
        <RootPanel background_color="#d9d9da">
            {notificationOpen && (
                <NotificationSystem
                    notificationText={notificationText}
                    notificationType={notificationType}
                    openState={notificationOpen}
                    setOpenState={setNotificationOpen}
                    onCloseCallback={notificationCloseCallback}
                />
            )}
            <CustomAppBar
                logoWidth="50px"
                logoHeight="50px"
                appBarTextColor="#003b5f"
                appBarColor="#f8f8f8"
                authButtonTextColor="#003b5f"
                routesInfo={[
                    ['/', 'Transcription'],
                    ['/about', 'About'],
                    ['/auth', '[auth]'],
                ]}
            />
            <main className="auth-layout">
                <section className="auth-card" aria-labelledby="login-title">
                    <LogoComponent width="84px" height="84px" dynamicSizing={false} />

                    <Typography id="login-title" component="h1" className="auth-heading">
                        {isRegistering ? 'Create an account' : 'Sign in to Pytacte'}
                    </Typography>
                    <Typography className="auth-description">
                        {isRegistering ? 'Register to get started with Pytacte.' : 'Sign in to continue to Pytacte.'}
                    </Typography>

                    <div className="auth-form">
                        <TextField
                            className="auth-field"
                            label="Email address"
                            type="email"
                            autoComplete="username"
                            required
                            fullWidth
                            onChange={(e) => setEmail(e.target.value)}
                        />
                        <TextField
                            className="auth-field"
                            label="Password"
                            type={passwordVisible ? 'text' : 'password'}
                            autoComplete="current-password"
                            required
                            fullWidth
                            slotProps={{
                                input: {
                                    endAdornment: (
                                        <InputAdornment position="end">
                                            <IconButton
                                                aria-label={passwordVisible ? 'Hide password' : 'Show password'}
                                                aria-pressed={passwordVisible}
                                                onClick={() => setPasswordVisible(!passwordVisible)}
                                                edge="end"
                                            >
                                                {passwordVisible ? <VisibilityOff /> : <Visibility />}
                                            </IconButton>
                                        </InputAdornment>
                                    ),
                                },
                            }}
                            onChange={(e) => setPassword(e.target.value)}
                        />
                        {isRegistering && (
                            <TextField
                                className="auth-field"
                                label="Repeat Password"
                                type={passwordVisible ? 'text' : 'password'}
                                autoComplete="current-password"
                                required
                                fullWidth
                                slotProps={{
                                    input: {
                                        endAdornment: (
                                            <InputAdornment position="end">
                                                <IconButton
                                                    aria-label={passwordVisible ? 'Hide password' : 'Show password'}
                                                    aria-pressed={passwordVisible}
                                                    onClick={() => setPasswordVisible(!passwordVisible)}
                                                    edge="end"
                                                >
                                                    {passwordVisible ? <VisibilityOff /> : <Visibility />}
                                                </IconButton>
                                            </InputAdornment>
                                        ),
                                    },
                                }}
                                onChange={(e) => setRepeatPassword(e.target.value)}
                            />
                        )}
                        <Button className="auth-submit" type="button" variant="contained" fullWidth onClick={() => handleAuthentication(false, email, password, repeatPassword, isRegistering, setNotificationText, setNotificationType, setNotificationOpen, setIsRegistering)}>
                            {isRegistering ? 'Register' : 'Sign in'}
                        </Button>
                        {!isRegistering && (
                            <Button className="auth-google-submit" type="button" variant="contained" fullWidth onClick={() => handleAuthentication(true, email, password, repeatPassword, isRegistering, setNotificationText, setNotificationType, setNotificationOpen)}>
                                <span className="auth-google-content">
                                    <img className="auth-google-logo" src={googleLogo} alt="" />
                                    <span>Sign in with Google</span>
                                </span>
                            </Button>
                        )}
                    </div>

                    {isRegistering && (
                        <Typography className="auth-register-prompt">
                            Already have an account?{' '}
                            <a className="auth-register-link" type="button" onClick={() => setIsRegistering(false)}>
                                Sign in
                            </a>
                        </Typography>
                    )}
                    {!isRegistering && (
                        <Typography className="auth-register-prompt">
                            New to Pytacte?{' '}
                            <a className="auth-register-link" type="button" onClick={() => setIsRegistering(true)}>
                                Register
                            </a>
                        </Typography>
                    )}
                </section>
            </main>
        </RootPanel>
    );
}

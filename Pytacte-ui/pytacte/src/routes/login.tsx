import { useState, useEffect } from 'react';
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
import logo from '../images/Firebase-Logo.png';

export const Route = createFileRoute('/login')({ component: Login });

function handleAuthentication(email: string, password: string, isRegistering: boolean) {
    if (isRegistering) {
        console.log('Registering with email:', email, 'and password:', password);
        // Implement registration logic here
    } else {
        console.log('Logging in with email:', email, 'and password:', password);
        // Implement login logic here
    }
}


function Login() {
    const [passwordVisible, setPasswordVisible] = useState(false);
    const [isRegistering, setIsRegistering] = useState(false);

    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [repeatPassword, setRepeatPassword] = useState('');


    return (
        <RootPanel background_color="#d9d9da">
            <CustomAppBar
                logoWidth="50px"
                logoHeight="50px"
                appBarTextColor="#003b5f"
                appBarColor="#f8f8f8"
                authButtonTextColor="#003b5f"
                routes={['Trancription', 'About', '[auth]']}
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
                        <Button className="auth-submit" type="button" variant="contained" fullWidth onClick={() => handleAuthentication(email, password, isRegistering)}>
                            {isRegistering ? 'Register' : 'Sign in'}
                        </Button>
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

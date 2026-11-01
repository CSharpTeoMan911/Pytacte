import * as React from 'react';
import { useState, useEffect } from 'react';
import AppBar from '@mui/material/AppBar';
import Box from '@mui/material/Box';
import Toolbar from '@mui/material/Toolbar';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import Menu from '@mui/material/Menu';
import MenuIcon from '@mui/icons-material/Menu';
import Container from '@mui/material/Container';
import Button from '@mui/material/Button';
import MenuItem from '@mui/material/MenuItem';
import LogoComponent from './LogoComponent';
import { getIfUserLoggedIn } from '../firebase/firebase_auth';


type Porps = {
  authButtonTextColor?: string | 'inherit';
  appBarTextColor?: string;
  appBarColor?: string;
  logoWidth?: number | string;
  logoHeight?: number | string;
  routes?: string[];
};

export default function CustomAppBar({ appBarTextColor, appBarColor, logoWidth, logoHeight, routes }: Porps) {

  const [pages, setPages] = useState<string[]>(routes || ['Home', 'About', 'Contact']);

  const [loggedIn, setLoggedIn] = useState<boolean>(false);

  useEffect(() => {
     async function checkAuthStatus() {
      console.log('Checking auth status...');
      if (pages.find((page) => page === '[auth]')) {
        setLoggedIn( await getIfUserLoggedIn());
        console.log('Logged in:', loggedIn);
        setPages(pages.map((p) => p === '[auth]' ? (loggedIn ? 'Logout' : 'Login') : p));
      }
      else{
        console.log('No auth route found in pages:', pages);
      }
    }
    checkAuthStatus();
  });



  const [anchorElNav, setAnchorElNav] = React.useState<null | HTMLElement>(null);
  const [anchorElUser, setAnchorElUser] = React.useState<null | HTMLElement>(null);

  const handleOpenNavMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorElNav(event.currentTarget);
  };

  const handleCloseNavMenu = () => {
    setAnchorElNav(null);
  };

  const handleCloseUserMenu = () => {
    setAnchorElUser(null);
  };

  return (
    <AppBar position="static" sx={{ backgroundColor: appBarColor, color: appBarTextColor, }}>
      <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:ital,wght@0,100..700;1,100..700&display=swap');
      </style>

      <Container maxWidth="xl">
        <Toolbar disableGutters>
          <LogoComponent width={logoWidth} height={logoHeight} sx={{ display: { xs: 'none', md: 'flex' }, mr: 1 }} />
          <Typography
            variant="h6"
            noWrap
            component="a"
            href="#app-bar-with-responsive-menu"
            sx={{
              marginRight: '40px',
              mr: 2,
              display: { xs: 'none', md: 'flex' },
              fontFamily: 'Roboto Mono, monospace',
              fontWeight: 700,
              letterSpacing: '.3rem',
              color: 'inherit',
              textDecoration: 'none',
              alignSelf: 'center',
            }}
          >
            Pytacte
          </Typography>

          <Box sx={{ flexGrow: 1, display: { xs: 'flex', md: 'none' } }}>
            {loggedIn && <IconButton
              size="large"
              aria-label="account of current user"
              aria-controls="menu-appbar"
              aria-haspopup="true"
              onClick={handleOpenNavMenu}
              color="inherit"
            >
              <MenuIcon />
            </IconButton>}
            {loggedIn && <Menu
              id="menu-appbar"
              anchorEl={anchorElNav}
              anchorOrigin={{
                vertical: 'bottom',
                horizontal: 'left',
              }}
              keepMounted
              transformOrigin={{
                vertical: 'top',
                horizontal: 'left',
              }}
              open={loggedIn && Boolean(anchorElNav)}
              onClose={handleCloseNavMenu}
              sx={{
                display: { xs: 'block', md: 'none' },
                '& .MuiPaper-root': { backgroundColor: appBarColor },
              }}
            >
              {pages.map((page) => (

                <MenuItem key={page} onClick={handleCloseNavMenu} sx={{ color: appBarTextColor }}>
                  <Typography sx={{ textAlign: 'center', color: appBarTextColor, fontFamily: 'Roboto Mono, monospace', fontWeight: 400, letterSpacing: '.05rem', fontSize: '0.800rem' }}>{page}</Typography>
                </MenuItem>
              ))}
            </Menu>}
          </Box>
          <LogoComponent width={logoWidth} height={logoHeight} sx={{ display: { xs: 'flex', md: 'none' }, mr: 1 }} />
          <Typography
            variant="h5"
            noWrap
            component="a"
            href="#app-bar-with-responsive-menu"
            sx={{
              mr: 2,
              display: { xs: 'flex', md: 'none' },
              flexGrow: 1,
              fontFamily: 'Roboto Mono, monospace',
              fontWeight: 700,
              letterSpacing: '.3rem',
              color: 'inherit',
              textDecoration: 'none',
            }}
          >
            Pytacte
          </Typography>
          {loggedIn && <Box sx={{ flexGrow: 1, display: { xs: 'none', md: 'flex', marginLeft: '50px' } }}>
            {pages.map((page) => (
              <Button
                key={page}
                onClick={handleCloseNavMenu}
                sx={{ my: 2, color: appBarTextColor, display: 'block', fontFamily: 'Roboto Mono, monospace', fontWeight: 500, letterSpacing: '.1rem', fontSize: '1rem', textTransform: 'none', marginRight: '20px', }}
              >
                {page}
              </Button>
            ))}
          </Box>}
          <Box sx={{ flexGrow: 0 }}>

            <Menu
              sx={{ mt: '45px' }}
              id="menu-appbar"
              anchorEl={anchorElUser}
              anchorOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              keepMounted
              transformOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              open={Boolean(anchorElUser)}
              onClose={handleCloseUserMenu}
            >

            </Menu>
          </Box>
        </Toolbar>
      </Container>
    </AppBar>
  );
}

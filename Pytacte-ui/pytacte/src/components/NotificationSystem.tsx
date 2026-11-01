import { useEffect } from 'react';
import CheckCircleOutlinedIcon from '@mui/icons-material/CheckCircleOutlined';
import CloseIcon from '@mui/icons-material/Close';
import ErrorOutlinedIcon from '@mui/icons-material/ErrorOutlined';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import WarningAmberOutlinedIcon from '@mui/icons-material/WarningAmberOutlined';
import IconButton from '@mui/material/IconButton';
import Popover from '@mui/material/Popover';
import Typography from '@mui/material/Typography';

type NotificationType = 'success' | 'error' | 'warning' | 'info';

type Props = {
    timeoutSeconds?: number;
    notificationText: string;
    notificationType: NotificationType;
    openState: boolean;
    setOpenState?: (open: boolean) => void;
    onCloseCallback?: () => void;
};

const notificationIcons = {
    success: CheckCircleOutlinedIcon,
    error: ErrorOutlinedIcon,
    warning: WarningAmberOutlinedIcon,
    info: InfoOutlinedIcon,
};

export default function NotificationSystem({
    notificationText,
    notificationType,
    openState,
    setOpenState,
    onCloseCallback,
    timeoutSeconds = 10,
}: Props) {
    useEffect(() => {
        if (!openState || timeoutSeconds <= 0) return;

        const timeout = window.setTimeout(() => {
            setOpenState?.(false);
            onCloseCallback?.();
        }, timeoutSeconds * 1000);

        return () => window.clearTimeout(timeout);
    }, [openState, timeoutSeconds, setOpenState, onCloseCallback]);

    const NotificationIcon = notificationIcons[notificationType];

    const handleClose = (_event: object, reason: string) => {
        // Keep the popover open when the user clicks outside it.
        if (reason === 'backdropClick') return;

        setOpenState?.(false);
        onCloseCallback?.();
    };

    const handleCloseButton = () => {
        setOpenState?.(false);
        onCloseCallback?.();
    };

    return (
        <Popover
            open={openState}
            onClose={handleClose}
            anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
            transformOrigin={{ vertical: 'top', horizontal: 'center' }}
            slotProps={{ paper: { className: 'notification-popover-paper' } }}
        >
            <div className={`notification-content notification-content--${notificationType}`} role="status">
                <NotificationIcon className="notification-icon" titleAccess={`${notificationType} notification`} />
                <Typography className="notification-text">{notificationText}</Typography>
                <IconButton
                    className="notification-close"
                    aria-label="Close notification"
                    size="small"
                    onClick={handleCloseButton}
                >
                    <CloseIcon fontSize="small" />
                </IconButton>
            </div>
        </Popover>
    );
}

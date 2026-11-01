import { BrowserView, MobileView, isMobile } from 'react-device-detect';
import type { ReactNode } from 'react';

type Props = {
    desktopChildren: ReactNode;
    mobileChildren:ReactNode;
}

const deviceSignals = {
    touchPoints: navigator.maxTouchPoints,

    coarsePointer: matchMedia('(pointer: coarse)').matches,

    anyCoarsePointer: matchMedia('(any-pointer: coarse)').matches,

    noHover: matchMedia('(hover: none)').matches,

    noAnyHover: matchMedia('(any-hover: none)').matches,
};

export default function DeviceSelector({ desktopChildren, mobileChildren }: Props) {

    const isProbablyMobile = deviceSignals.anyCoarsePointer || deviceSignals.coarsePointer || deviceSignals.noHover || deviceSignals.noAnyHover;

    console.debug('DeviceSelector: isMobile:', isMobile, 'isProbablyMobile:', isProbablyMobile);
    console.log('DeviceSelector: isMobile:', isMobile, 'isProbablyMobile:', isProbablyMobile);

    if (isMobile && isProbablyMobile) {
        return (
            <MobileView>
                {mobileChildren}
            </MobileView>
        );
    }
    else {
        return (
            <BrowserView>
                {desktopChildren}
            </BrowserView>
        );
    }
}
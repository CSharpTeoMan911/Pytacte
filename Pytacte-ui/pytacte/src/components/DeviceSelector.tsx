import { BrowserView, MobileView, isMobile } from 'react-device-detect';
import type { ReactNode } from 'react';

type Props = {
    desktopChildren: ReactNode;
    mobileChildren:ReactNode;
    desktopClassName?: string;
    mobileClassName?: string;
}

const deviceSignals = {
    touchPoints: navigator.maxTouchPoints,

    coarsePointer: matchMedia('(pointer: coarse)').matches,

    anyCoarsePointer: matchMedia('(any-pointer: coarse)').matches,

    noHover: matchMedia('(hover: none)').matches,

    noAnyHover: matchMedia('(any-hover: none)').matches,
};

export default function DeviceSelector({ desktopChildren, mobileChildren, desktopClassName, mobileClassName }: Props) {

    const isProbablyMobile = deviceSignals.anyCoarsePointer || deviceSignals.coarsePointer || deviceSignals.noHover || deviceSignals.noAnyHover;


    if (isMobile && isProbablyMobile) {
        return (
            <MobileView className={mobileClassName}>
                {mobileChildren}
            </MobileView>
        );
    }
    else {
        return (
            <BrowserView className={desktopClassName}>
                {desktopChildren}
            </BrowserView>
        );
    }
}

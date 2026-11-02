import * as React from 'react';

import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import FormControl, { type FormControlPropsSizeOverrides } from '@mui/material/FormControl';
import type { OverridableStringUnion } from '@mui/types'
import Select from '@mui/material/Select';
import type { SelectChangeEvent } from '@mui/material/Select';
import Typography from '@mui/material/Typography';


type Props = {
    label?: string | ''
    size?: OverridableStringUnion<"medium" | "small", FormControlPropsSizeOverrides>
    minWidth?: string | 'default'
    menuContents: string[]
    menuBackgroundColor?: string | 'default'
    textColor?: string | 'default'
    borderColor?: string | 'default'
}

const ITEM_HEIGHT = 48;
const ITEM_PADDING_TOP = 8;
const MenuProps = {
    slotProps: {
        paper: {
            style: {
                maxHeight: ITEM_HEIGHT * 4.5 + ITEM_PADDING_TOP,
                width: 250,
                backgroundColor: '#f5f5f5',
            },
        },
    },
};

export default function CustomSelectionField({label, menuContents, menuBackgroundColor, textColor, borderColor, minWidth, size }: Props) {

    const MenuProps = {
        slotProps: {
            paper: {
                sx: {
                    backgroundColor: menuBackgroundColor,
                },
            },
        },
    };
    const [sttModel, setSttModel] = React.useState(menuContents[0] ?? '');

    React.useEffect(() => {
        if (menuContents.length > 0 && !menuContents.includes(sttModel)) {
            setSttModel(menuContents[0]);
        }
    }, [menuContents, sttModel]);

    const handleChange = (event: SelectChangeEvent) => {
        setSttModel(event.target.value);
    };

    return (
        <FormControl sx={{ m: 1, minWidth: minWidth }} size={size}>
            <InputLabel id="demo-simple-select-required-label" sx={{ color: textColor, fontSize: '1rem', textAlign: 'center', '&.Mui-focused': { color: textColor } }}>
                {label}
            </InputLabel>
            <Select
                labelId="demo-simple-select-required-label"
                id="demo-simple-select-required"
                value={sttModel}
                label={label}
                onChange={handleChange}
                MenuProps={MenuProps}
                sx={{
                    height: 'fit-content',
                    backgroundColor: 'transparent',
                    '& .MuiOutlinedInput-notchedOutline': {
                        borderColor: borderColor,
                    },
                    '&:hover .MuiOutlinedInput-notchedOutline': {
                        borderColor: borderColor,
                    },
                    '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                        borderColor: borderColor,
                    },
                    '& .MuiSelect-icon': {
                        color: textColor,
                    },
                    '&.MuiSelect-paper': {
                        backgroundColor: '#252525'
                    }
                }}
            >


                {
                    menuContents.map((model) => ((
                        <MenuItem key={model} value={model} sx={{

                        }}>
                            <Typography sx={{
                                color: textColor,
                                fontSize: '.9em'
                            }}>
                                {model}
                            </Typography>
                        </MenuItem>)
                    ))
                }
            </Select>
        </FormControl>
    );
}

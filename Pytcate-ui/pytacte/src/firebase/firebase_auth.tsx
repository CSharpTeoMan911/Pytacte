import { app } from './firebase_app'
import { getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword, validatePassword, signOut } from "firebase/auth";


type compositeResult = [boolean, string]

const auth = getAuth(app);

export async function validateAccountPassword(password: string): Promise<compositeResult> {
    const status = await validatePassword(auth, password);
    const needsNumbersOrSymbols = !status.containsNumericCharacter || !status.containsNumericCharacter;
    const needsMinLength = !status.meetsMinPasswordLength;

    const message = needsNumbersOrSymbols ? 'Ensure that the password contains numbers and symbols.' : needsMinLength ? 'The password needs to be at least 10 characters long.' : 'Account creation successful';

    return [status.isValid, message];
}

export async function registerAccount(email: string, password: string): Promise<compositeResult> {

    try {

        const [status, message] = await validateAccountPassword(password);

        if (status) {
            const userCredential = await createUserWithEmailAndPassword(auth, email, password);
            const user = userCredential.user;
        }

        return [status, message];
    }
    catch (error) {
        return [false, error as string];
    }
}


export async function loginAccount(email: string, password: string): Promise<compositeResult> {
    try {
        const userCredential = await signInWithEmailAndPassword(auth, email, password)
        const user = userCredential.user;

        return [false, 'Login Successful'];
    }
    catch (error) {
        return [false, error as string];
    }
}


export async function logoutAccount() : Promise<compositeResult> {
    try {
        await signOut(auth);
        return [true, 'Logout Successful'];
    }
    catch (error) {
        return [false, error as string];
    }
}


export function getIfUserLoggedIn():boolean {
    if(auth.currentUser)
        return true;
    else
        return false;
}

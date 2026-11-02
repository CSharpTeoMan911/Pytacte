import { app } from './firebase_app'
import { getAuth, createUserWithEmailAndPassword, sendEmailVerification, applyActionCode, signInWithEmailAndPassword, validatePassword, signOut, GoogleAuthProvider, signInWithPopup } from "firebase/auth";


type compositeResult = [boolean, string]

const auth = getAuth(app);
const provider = new GoogleAuthProvider();


async function validateAccountPassword(password: string): Promise<compositeResult> {
    const status = await validatePassword(auth, password);
    const policy = status.passwordPolicy;

    const minPasswordLength = policy && policy.customStrengthOptions.minPasswordLength;
    const maxPasswordLength = policy && policy.customStrengthOptions.maxPasswordLength;


    const needsNumeric = !(status.containsNumericCharacter !== undefined ? status.containsNumericCharacter : true);
    const needsSymbol = !(status.containsNonAlphanumericCharacter !== undefined ? status.containsNonAlphanumericCharacter : true);
    const needsMinLength = !(status.meetsMinPasswordLength !== undefined ? status.meetsMinPasswordLength : true);
    const needsMaxLength = !(status.meetsMaxPasswordLength !== undefined ? status.meetsMaxPasswordLength : true);
    const needsUppercase = !(status.containsUppercaseLetter !== undefined ? status.containsUppercaseLetter : true);
    const needsLowercase = !(status.containsLowercaseLetter !== undefined ? status.containsLowercaseLetter : true);

    const message = needsNumeric ? 'The password must contain at least one number.' : (needsSymbol ? 'The password must contain at least one symbol.' : (needsMinLength ? `The password needs to be at least ${minPasswordLength} characters long.` : (needsMaxLength ? `The password is too long. It must be at most ${maxPasswordLength} characters long.` : (needsUppercase ? 'The password must contain at least one uppercase letter.' : (needsLowercase ? 'The password must contain at least one lowercase letter.' : 'Account creation successful')))));

    return [status.isValid && !needsNumeric && !needsSymbol && !needsMinLength && !needsMaxLength && !needsUppercase && !needsLowercase, message];
}

export async function registerAccount(email: string, password: string): Promise<compositeResult> {

    try {

        const [status, message] = await validateAccountPassword(password);

        if (status) {
            const userCredential = await createUserWithEmailAndPassword(auth, email, password);
            const user = userCredential.user;
            await sendEmailVerification(user);
            // await applyActionCode(auth, code);
        }
        
        console.log('Account creation status:', status, 'Message:', message);
        return [status, message];
    }
    catch (error) {
        switch (error) {
            case 'Firebase: Error (auth/email-already-in-use)':
                console.log('Firebase: Error (The email address is already in use by another account.)');
                return [false, 'The email address is already in use by another account.'];
            case 'Firebase: Error (auth/invalid-email)':
                console.log('Firebase: Error (The email address is not valid.)');
                return [false, 'The email address is not valid.'];
            case 'Firebase: Error (auth/weak-password)':
                console.log('Firebase: Error (The password is too weak.)');
                return [false, 'The password is too weak.'];
            default:
                console.log('Other error occurred:', error);
                return [false, typeof error === 'string' ? error : (error as Error).message];
        }
    }
}


export async function loginAccount(email: string, password: string): Promise<compositeResult> {
    try {
        const userCredential = await signInWithEmailAndPassword(auth, email, password)
        const user = userCredential.user;

        return [true, 'Login Successful'];
    }
    catch (error) {
        return [false, error as string];
    }
}


export async function loginWithGoogle(): Promise<compositeResult> {
    try {
        const userCredential = await signInWithPopup(auth, provider);

        // # If Google services need to be accessed, the following code can be used to retrieve the access token and user information. For now, it is commented out as it is not needed for basic authentication.
        // const credential = await GoogleAuthProvider.credentialFromResult(userCredential);
        // const token = credential && credential.accessToken;

        // The signed-in user info.
        const user = userCredential.user;
        const googleUid = user.providerData.find(
            (profile) => profile.providerId === 'google.com'
        )?.uid;

        return [true, 'Login Successful'];
    }
    catch (error) {
        return [false, error as string];
    }
}


export async function logoutAccount(): Promise<compositeResult> {
    try {
        await signOut(auth);
        return [true, 'Logout Successful'];
    }
    catch (error) {
        return [false, error as string];
    }
}


export function getIfUserLoggedIn(): boolean {
    if (auth.currentUser)
        return true;
    else
        return false;
}

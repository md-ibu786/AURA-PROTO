/**
 * ============================================================================
 * FILE: firebaseClient.ts
 * LOCATION: frontend/src/api/firebaseClient.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Firebase SDK configuration and initialization for the frontend.
 *    Provides Firebase Auth instance for authentication operations.
 *
 * ROLE IN PROJECT:
 *    Central Firebase configuration used by auth store and components.
 *    All Firebase services should be imported from this file.
 *
 * KEY EXPORTS:
 *    - app: Firebase App instance
 *    - auth: Firebase Auth instance
 *
 * DEPENDENCIES:
 *    - External: firebase/app, firebase/auth
 *
 * USAGE:
 *    import { auth } from '../api/firebaseClient';
 *    import { signInWithEmailAndPassword } from 'firebase/auth';
 * ============================================================================
 */

import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { initializeAppCheck, ReCaptchaEnterpriseProvider } from 'firebase/app-check';

// Firebase configuration from environment variables
// These should match your Firebase project settings
const firebaseConfig = {
    apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
    authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
    projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
    storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
    appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase Auth
const auth = getAuth(app);

// Initialize App Check
// Wrapped in try-catch to prevent crashes during development if not configured
let appCheck;
try {
    if (typeof window !== 'undefined') {
        const siteKey = import.meta.env.VITE_RECAPTCHA_ENTERPRISE_SITE_KEY;
        if (siteKey && siteKey !== 'placeholder_site_key') {
            appCheck = initializeAppCheck(app, {
                provider: new ReCaptchaEnterpriseProvider(siteKey),
                isTokenAutoRefreshEnabled: true
            });
        }
    }
} catch (error) {
    console.warn('Firebase App Check initialization failed:', error);
}

export { app, auth, appCheck };

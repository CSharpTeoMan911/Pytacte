// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyAoDvQYCQv97rCua9zEACmCwMrRlNSusOA",
  authDomain: "pytacte.firebaseapp.com",
  projectId: "pytacte",
  storageBucket: "pytacte.firebasestorage.app",
  messagingSenderId: "332750331423",
  appId: "1:332750331423:web:c7209628db4703c7fdbf2a",
  measurementId: "G-VXGH185Z03"
};

// Initialize Firebase
export const app = initializeApp(firebaseConfig);

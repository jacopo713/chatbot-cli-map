// Firebase configuration and initialization
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";
import { getStorage } from "firebase/storage";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyBPBQBjhXYMdQSloTMTQWDlMno7qU08DXQ",
  authDomain: "chat-cli-map.firebaseapp.com",
  projectId: "chat-cli-map",
  storageBucket: "chat-cli-map.firebasestorage.app",
  messagingSenderId: "839617452578",
  appId: "1:839617452578:web:b5c4ee323b5047bc1ac87b",
  measurementId: "G-HHTLSTL5CL"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase services
export const auth = getAuth(app);
export const db = getFirestore(app);
export const storage = getStorage(app);

// Initialize Analytics (only in browser)
export const analytics = typeof window !== 'undefined' ? getAnalytics(app) : null;

export default app;
import {initializeApp} from "firebase/app";
import { getStorage } from "firebase/storage";

const firebaseConfig = {
  apiKey: "AIzaSyB-2ZwJxZ_dAJk4j0V3bSzwWNUamJzTxo8",
  authDomain: "genai-project-fb7a5.firebaseapp.com",
  projectId: "genai-project-fb7a5",
  storageBucket: "genai-project-fb7a5.firebasestorage.app",
  messagingSenderId: "632005784504",
  appId: "1:632005784504:web:18e24bea531a62efb8154d",
  measurementId: "G-FDSZB3GYCF"
};

export const app = initializeApp(firebaseConfig);
export const storage = getStorage(app);
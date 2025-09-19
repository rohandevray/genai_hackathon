
import './App.css';
import Home from "./pages/Home";
import MarkdownPage from './components/MarkDownPage';
import GeneratedFilesPage from './components/GenerateFilesPage';
import { BrowserRouter as Router, Routes,Route } from 'react-router-dom';
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import AuthForm from './auth/AuthForm';


function App() {
  return (
    <>
   <Router>
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/markdown" element={<MarkdownPage />} />
      <Route path="/generated-files" element={<GeneratedFilesPage />} />
      <Route path='/login'  element={<AuthForm />} />
    </Routes>
  </Router>
   <ToastContainer
        position="top-right"
        autoClose={4000}       // 4 seconds
        hideProgressBar={false}
        newestOnTop={true}
        closeOnClick
        pauseOnHover
        draggable
        theme="colored"       // nice colorful styles
      />
  </>
  );
}

export default App;

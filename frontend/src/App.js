
import './App.css';
import Home from "./pages/Home";
import MarkdownPage from './components/MarkDownPage';
import GeneratedFilesPage from './components/GenerateFilesPage';
import { BrowserRouter as Router, Routes,Route } from 'react-router-dom';

function App() {
  return (
   <Router>
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/markdown" element={<MarkdownPage />} />
       <Route path="/generated-files" element={<GeneratedFilesPage />} />
    </Routes>
  </Router>
  );
}

export default App;

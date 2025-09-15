import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import FileUpload from "../components/FileUpload";
import RequirementList from "../components/RequirementList";
import TestCaseTable from "../components/TestCaseTable";
import { generateTestCases } from "../api";
import styles from "./Home.module.css";

export default function Home() {
  const [requirements, setRequirements] = useState([]);
  const [testCases, setTestCases] = useState([]);
  const [jiraConnected, setJiraConnected] = useState(false);
  const navigate = useNavigate();

  // This function is passed to FileUpload
  const handleUpload = (uploadedRequirements, selectedCompliance) => {
    // Navigate to MarkdownPage with state
    navigate("/markdown", {
      state: { requirements: uploadedRequirements, compliance: selectedCompliance }
    });
  };

  const handleGenerate = async (reqId) => {
    try {
      const { data } = await generateTestCases(reqId);
      setTestCases(data.testCases);
    } catch (err) {
      alert("Failed to generate test cases!");
    }
  };

  const handleConnectJira = () => { 
    window.location.href = "http://localhost:8000/connect-jira";
  };

  return (
    <div className={styles.page}>
      <motion.nav
        className={styles.navbar}
        initial={{ y: -50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }} 
        transition={{ duration: 0.5 }}
      >
        <div className={styles.logo}>🚀 TestGenAI</div>
       <button
          onClick={handleConnectJira}
          className={jiraConnected ? styles.connectedBtn : styles.loginBtn}
        >
          {jiraConnected ? "✅ Connected to Jira" : "Connect Jira"}
        </button>
      </motion.nav>

      <motion.header
        className={styles.hero}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1 }}
      >
        <h1 className={styles.title}>AI-Powered Test Case Generator</h1>
        <p className={styles.subtitle}>
          Upload your requirements and let AI generate precise test cases automatically!
        </p>
      </motion.header>

      <motion.section
        className={styles.content}
        initial={{ x: -100, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.8 }}
      >
        <FileUpload onUpload={handleUpload} />

        {requirements.length > 0 && (
          <RequirementList
            requirements={requirements}
            onGenerate={handleGenerate}
          />
        )}

        {testCases.length > 0 && <TestCaseTable testCases={testCases} />}
      </motion.section>
    </div>
  );
}

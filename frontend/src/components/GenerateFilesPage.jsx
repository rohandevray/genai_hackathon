import { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { Download } from "lucide-react";
import { FaFilePdf, FaFileWord, FaHtml5 } from "react-icons/fa";
import { VscCode } from "react-icons/vsc";
import styles from "./GeneratedFilesPage.module.css";
import { toast } from "react-toastify";
import axios from "axios";

export default function GeneratedFilesPage() {
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const jiraConnected = queryParams.get("connected") === "jira";

  // If coming fresh from generator, get formats from state and save to localStorage
  const initialFormats =
    location.state?.formats ||
    JSON.parse(localStorage.getItem("formats") || "[]");

  const [formats, setFormats] = useState(initialFormats);
  const [showYesNo, setShowYesNo] = useState(!jiraConnected);
  const [showPromptInput, setShowPromptInput] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [submittedPrompt, setSubmittedPrompt] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingUploads, setLoadingUploads] = useState({});
  const [feedbackCount, setFeedbackCount] = useState(0);
  const maxFeedback = 3;

  // Save formats if available
  useEffect(() => {
    if (initialFormats.length > 0) {
      localStorage.setItem("formats", JSON.stringify(initialFormats));
    }
  }, [initialFormats]);

  // Show success toast only once when redirected back
  useEffect(() => {
    if (jiraConnected) {
      toast.success("✅ Jira connected successfully!");
    }
  }, [jiraConnected]);

  // Dummy test cases per format
  const dummyTestCases = {
    pdf: [
      {
        summary: "Verify PDF header is correct",
        description: "Open the PDF and check the title section.",
      },
      {
        summary: "Check PDF footer",
        description: "Ensure page numbers are visible.",
      },
    ],
    word: [
      {
        summary: "Verify Word document formatting",
        description: "Headings should use H1 style.",
      },
      {
        summary: "Spell check document",
        description: "Run spell check across the document.",
      },
    ],
    html: [
      {
        summary: "Check HTML page loads",
        description: "Open in browser and verify no console errors.",
      },
      {
        summary: "Validate HTML tags",
        description: "Ensure all tags are properly closed.",
      },
    ],
    xml: [
      {
        summary: "Validate XML schema",
        description: "Run against provided XSD schema.",
      },
      {
        summary: "Check XML root element",
        description: "Ensure <root> is present.",
      },
    ],
  };

  const getFileIcon = (format) => {
    switch (format.toLowerCase()) {
      case "pdf":
        return <FaFilePdf color="#E50914" size={30} />;
      case "word":
        return <FaFileWord color="#2B579A" size={30} />;
      case "html":
        return <FaHtml5 color="#E44D26" size={30} />;
      case "xml":
        return <VscCode color="#FF9800" size={30} />;
      default:
        return <VscCode color="#6B7280" size={30} />;
    }
  };

  const getDummyFileName = (format) => {
    switch (format.toLowerCase()) {
      case "word":
        return "dummy.docx";
      case "html":
        return "dummy.html";
      case "pdf":
        return "dummy.pdf";
      case "xml":
        return "dummy.xml";
      default:
        return `dummy.${format.toLowerCase()}`;
    }
  };

  const handleDownload = (format) => {
    toast.info(`Downloading ${getDummyFileName(format)}...`);
  };

  const handleYesClick = () => {
    setShowYesNo(false);
    // Show Jira connect (redirect)
    const state = "user123";
    const url = `https://auth.atlassian.com/authorize?audience=api.atlassian.com&client_id=3ewrPVgbajY6Or7gXCBhSnilSkphliMk&scope=read:jira-work write:jira-work&redirect_uri=http://localhost:8000/jira/callback&state=${state}&response_type=code&prompt=consent`;
    window.location.href = url;
  };

  const handleNoClick = () => {
    if (feedbackCount >= maxFeedback) {
      toast.error("You have reached the maximum feedback submissions.");
      return;
    }
    setShowYesNo(false);
    setShowPromptInput(true);
  };

  const handlePromptSubmit = () => {
    if (!prompt.trim()) {
      toast.error("Please enter a valid feedback prompt.");
      return;
    }

    toast.info("Regenerating files... Please wait.");
    setLoading(true);

    setTimeout(() => {
      setSubmittedPrompt(prompt);
      setFeedbackCount((prev) => prev + 1);

      toast.success("Files regenerated successfully!");
      setLoading(false);

      // Reset flow
      setShowPromptInput(false);
      setPrompt("");
      setShowYesNo(true);
    }, 5000);
  };

  const handleUploadToJira = async (format) => {
    const fileName = getDummyFileName(format);
    const testCases = dummyTestCases[format.toLowerCase()] || [];

    setLoadingUploads((prev) => ({ ...prev, [fileName]: true }));

    try {
      const res = await axios.post("http://localhost:8000/jira/create-issues", {
        projectKey: "SMS", // replace with your project key
        testCases,
      });

      if (res.status === 200) {
        toast.success(`📌 Created Jira issues from ${fileName}!`);
      } else {
        toast.error(`❌ Failed to create Jira issues from ${fileName}`);
      }
    } catch (err) {
      console.error(err);
      toast.error(`⚠️ Error creating Jira issues from ${fileName}`);
    } finally {
      setLoadingUploads((prev) => ({ ...prev, [fileName]: false }));
    }
  };

  return (
    <div className={styles.page}>
      <motion.h1
        className={styles.title}
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        Generated Files
      </motion.h1>

      <div className={styles.fileList}>
        {formats.map((format, idx) => {
          const testCases = dummyTestCases[format.toLowerCase()] || [];
          const fileName = getDummyFileName(format);

          return (
            <motion.div
              key={idx}
              className={styles.fileCard}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: idx * 0.1 }}
            >
              <div className={styles.fileHeader}>
                <div className={styles.fileInfo}>
                  {getFileIcon(format)}
                  <span className={styles.fileName}>{fileName}</span>
                </div>
                <div className={styles.actions}>
                  <motion.button
                    className={styles.downloadBtn}
                    whileHover={{ scale: 1.1, rotate: 5 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={() => handleDownload(format)}
                  >
                    <Download size={20} />
                  </motion.button>

                  {jiraConnected && (
                    <button
                      className={styles.uploadBtn}
                      onClick={() => handleUploadToJira(format)}
                      disabled={loadingUploads[fileName]}
                    >
                      {loadingUploads[fileName] ? "Uploading..." : "Upload"}
                    </button>
                  )}
                </div>
              </div>

              <div className={styles.filePreview}>
                {loading
                  ? "⏳ Regenerating files... Please wait."
                  : testCases.length > 0 ? (
                      <ul>
                        {testCases.map((tc, i) => (
                          <li key={i}>
                            <strong>{tc.summary}</strong>: {tc.description}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      "Preview not available"
                    )}
              </div>
            </motion.div>
          );
        })}
      </div>

      {showYesNo && !loading && !jiraConnected && (
        <motion.div
          className={styles.yesNoContainer}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <button className={styles.yesBtn} onClick={handleYesClick}>
            Yes
          </button>
          <button className={styles.noBtn} onClick={handleNoClick}>
            No
          </button>
        </motion.div>
      )}

      {showPromptInput && !loading && (
        <motion.div
          className={styles.promptContainer}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <h3>Enter your feedback instructions</h3>
          <textarea
            className={styles.promptBox}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Write your feedback..."
          />
          <button className={styles.submitBtn} onClick={handlePromptSubmit}>
            Submit
          </button>
        </motion.div>
      )}
    </div>
  );
}

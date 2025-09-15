import { useState } from "react";
import { motion } from "framer-motion";
import { Upload } from "lucide-react";
import { useNavigate } from "react-router-dom";
import styles from "./FileUpload.module.css";
import { FaSpinner } from "react-icons/fa";
import { HiArrowNarrowRight } from "react-icons/hi";

const compliancesList = ["FDA", "IEC 62304", "ISO 9001", "ISO 13485", "ISO 27001"];
const dummyRequirements = ["Requirement 1", "Requirement 2", "Requirement 3"];

export default function FileUpload() {
  const [selectedCompliances, setSelectedCompliances] = useState([]);
  const [testCaseInput, setTestCaseInput] = useState("");
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleComplianceToggle = (compliance) => {
    if (selectedCompliances.includes(compliance)) {
      setSelectedCompliances(selectedCompliances.filter((c) => c !== compliance));
    } else {
      setSelectedCompliances([...selectedCompliances, compliance]);
    }
  };

  const handleProceed = () => {
    // ✅ text is always required
    if (testCaseInput.trim() === "") {
      alert("⚠ Please enter specifications before proceeding!");
      return;
    }

    // ✅ Case 1: Manual Specs (no file upload → needs compliance)
    if (selectedFiles.length === 0) {
      if (selectedCompliances.length === 0) {
        alert("⚠ Please select at least one compliance when not uploading files!");
        return;
      }

      navigate("/markdown", {
        state: {
          requirements: dummyRequirements,
          compliance: selectedCompliances.join(", "),
          testCases: testCaseInput.trim(),
          uploadedFiles: [],
        },
      });
      return;
    }

    // ✅ Case 2: File Upload (compliances optional)
    if (selectedFiles.length > 0) {
      navigate("/markdown", {
        state: {
          requirements: dummyRequirements,
          compliance: selectedCompliances.length > 0 ? selectedCompliances.join(", ") : "Not Selected",
          testCases: testCaseInput.trim(),
          uploadedFiles: selectedFiles.map((file) => file.name),
        },
      });
    }
  };

  const handleUploadLocal = (event) => {
    const files = Array.from(event.target.files);
    if (files.length > 0) {
      setLoading(true);
      setTimeout(() => {
        setSelectedFiles(files);
        setLoading(false);
      }, 2000);
    }
  };

  const handleUploadedFileClick = () => {
    if (selectedFiles.length > 0) {
      navigate("/markdown", {
        state: {
          requirements: dummyRequirements,
          compliance: selectedCompliances.length > 0 ? selectedCompliances.join(", ") : "Not Selected",
          testCases: testCaseInput.trim(),
          uploadedFiles: selectedFiles.map((file) => file.name),
        },
      });
    }
  };

  const truncateFileNames = (files, maxLength = 25) => {
    if (files.length === 0) return "Upload Local Files (Optional)";
    if (files.length === 1) {
      return files[0].name.length <= maxLength
        ? files[0].name
        : files[0].name.slice(0, maxLength) + "...";
    }
    return `${files.length} files selected`;
  };

  return (
    <motion.div
      className={styles.uploadWrapper}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      {/* Title */}
      <motion.h2
        className={styles.pageTitle}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        Generate Test Cases
      </motion.h2>

      {/* Multi-select compliances */}
      <div className={styles.complianceContainer}>
        <label className={styles.label}>Select Compliances:</label>
        <div className={styles.multiSelectContainer}>
          {compliancesList.map((compliance) => {
            const isDisabled = selectedFiles.length > 0;
            return (
            <motion.button
              key={compliance}
              className={`${styles.complianceBtn} ${
                selectedCompliances.includes(compliance) ? styles.selected : ""
              }`}
              whileTap={{ scale: 0.95 }}
              onClick={() => handleComplianceToggle(compliance)}
              disabled={isDisabled}
            >
              {compliance}
            </motion.button>
            );
          })}

        </div>
      </div>

      {/* Specifications Input Box */}
      <div className={styles.inputBoxWrapper}>
        <label className={styles.label}>Describe Specifications:</label>
        <motion.textarea
          className={styles.inputBox}
          placeholder="Write your specifications here..."
          value={testCaseInput}
          onChange={(e) => setTestCaseInput(e.target.value)}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        />
      </div>

      {/* Buttons */}
      <div className={styles.buttonsContainer}>
        {/* Proceed Button */}
        <motion.button
          className={styles.proceedBtn}
          whileHover={{ scale: 1.08 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleProceed}
        >
          <span className={styles.proceedText}>Proceed</span>
          <HiArrowNarrowRight size={22} className={styles.proceedIcon} />
        </motion.button>

        {/* Hidden file input */}
        <input
          id="file-upload"
          type="file"
          accept=".pdf"
          multiple
          style={{ display: "none" }}
          onChange={handleUploadLocal}
        />

        {/* Upload Button */}
        <motion.label
          htmlFor={selectedFiles.length === 0 ? "file-upload" : undefined}
          className={styles.uploadOnlyBtn}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={selectedFiles.length > 0 ? handleUploadedFileClick : undefined}
        >
          {loading ? (
            <FaSpinner size={20} className={`${styles.icon} ${styles.spin}`} />
          ) : (
            <Upload size={20} className={styles.icon} />
          )}
          {loading
            ? "Uploading..."
            : truncateFileNames(selectedFiles)}
        </motion.label>
      </div>
    </motion.div>
  );
}

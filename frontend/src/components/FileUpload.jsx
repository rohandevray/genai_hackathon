import { useState } from "react";
import { motion } from "framer-motion";
import { Upload } from "lucide-react";
import { useNavigate } from "react-router-dom";
import styles from "./FileUpload.module.css";
import { FaSpinner } from "react-icons/fa";
import { HiArrowNarrowRight } from "react-icons/hi";
import { toast } from "react-toastify";
import { ref, uploadBytesResumable, getDownloadURL } from "firebase/storage";
import { collection, addDoc } from "firebase/firestore";
import { storage, db } from "./firebase";

const compliancesList = ["FDA", "IEC 62304", "ISO 9001", "ISO 13485", "ISO 27001"];
const dummyRequirements = ["Requirement 1", "Requirement 2", "Requirement 3"];

export default function FileUpload() {
  const [selectedCompliances, setSelectedCompliances] = useState([]);
  const [testCaseInput, setTestCaseInput] = useState("");
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fileURLs, setFileURLs] = useState([]);
  const [progress, setProgress] = useState(0);
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
    toast.warn("Please describe specifications to proceed!");
    return;
  }

  // ✅ At least compliance OR file required
  if (selectedCompliances.length === 0 && selectedFiles.length === 0) {
    toast.warn("Please select at least one compliance OR upload files!");
    return;
  }

  // Proceed with navigation
  navigate("/markdown", {
    state: {
      requirements: dummyRequirements,
      compliance:
        selectedCompliances.length > 0
          ? selectedCompliances.join(", ")
          : "Not Selected",
      testCases: testCaseInput.trim(),
      uploadedFiles: selectedFiles.map((file) => file.name),
    },
  });
};
  const handleUploadLocal = (event) => {
    // const files = Array.from(event.target.files);
    const files = Array.from(event.target.files);

    if (files.length === 0)  return;

    setLoading(true);
    setProgress(0);
    console.log("Uploading files:", files.map(file => file.name));


    const file = files[0]; // Only upload the first file for simplicit
    const storageRef = ref(storage, `uploads/${Date.now()}-${file.name}`);
    const uploadTask = uploadBytesResumable(storageRef, file);

    uploadTask.on(
      "state_changed",
      (snapshot) => {   
        const percent = Math.round((snapshot.bytesTransferred / snapshot.totalBytes) * 100);
        setProgress(percent);
        console.log(`Upload is ${percent}% done`);
      },
      (error) => {
        console.error("Upload failed:", error);     
        toast.error("Upload failed!");
        setLoading(false);
      },
      async () => {
       const downloadURL = await getDownloadURL(uploadTask.snapshot.ref);
       console.log("✅ File uploaded:", downloadURL);
        setFileURLs((prev) => [...prev, downloadURL]);
        // You can also save metadata to Firestore here if needed 
        setSelectedFiles([file]);
        setLoading(false);
        toast.success("File uploaded successfully!");
     }
    );

  };


  const handleUploadedFileClick = () => {
  if (fileURLs.length > 0) {
    navigate("/markdown", {
      state: {
        requirements: dummyRequirements,
        compliance:
          selectedCompliances.length > 0
            ? selectedCompliances.join(", ")
            : "Not Selected",
        testCases: testCaseInput.trim(),
        uploadedFiles: selectedFiles.map((file) => file.url), // ✅ real GCS URLs stored in Firestore
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
  
            return (
            <motion.button
              key={compliance}
              className={`${styles.complianceBtn} ${
                selectedCompliances.includes(compliance) ? styles.selected : ""
              }`}
              whileTap={{ scale: 0.95 }}
              onClick={() => handleComplianceToggle(compliance)}
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

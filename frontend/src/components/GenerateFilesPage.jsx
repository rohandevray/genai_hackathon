import { useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { Download } from "lucide-react";
import { FaFilePdf, FaFileWord, FaHtml5 } from "react-icons/fa";
import { VscCode } from "react-icons/vsc";
import styles from "./GeneratedFilesPage.module.css";

export default function GeneratedFilesPage() {
  const location = useLocation();
  const { formats } = location.state || { formats: [] };

  // Dummy file contents based on file type
  const dummyContents = {
    html: `<!DOCTYPE html>
<html>
  <head>
    <title>Dummy HTML</title>
  </head>
  <body>
    <h1>Hello, Rohan!</h1>
    <p>This is a dummy HTML preview.</p>
  </body>
</html>`,
    xml: `<root>
  <user>
    <name>Rohan</name>
    <role>Developer</role>
    <email>rohan@example.com</email>
  </user>
</root>`,
    word: `This is a dummy Word document preview.
This represents a sample test case summary.`,
    pdf: `This is a dummy PDF preview.
PDF content can't be displayed directly, but this is sample extracted text.`,
  };

  // Get truncated content (first few lines)
  const getTruncatedContent = (format) => {
    const content = dummyContents[format.toLowerCase()] || "No preview available";
    const lines = content.split("\n").slice(0, 6).join("\n");
    return lines + (content.split("\n").length > 6 ? "\n..." : "");
  };

  // Get icon for each file type
  const getFileIcon = (format) => {
    switch (format.toLowerCase()) {
      case "pdf":
        return <FaFilePdf className={styles.fileIcon} color="#E50914" size={30} />;
      case "word":
        return <FaFileWord className={styles.fileIcon} color="#2B579A" size={30} />;
      case "html":
        return <FaHtml5 className={styles.fileIcon} color="#E44D26" size={30} />;
      case "xml":
        return <VscCode className={styles.fileIcon} color="#FF9800" size={30} />;
      default:
        return <VscCode className={styles.fileIcon} color="#6B7280" size={30} />;
    }
  };

  // Get proper dummy filename based on format
  const getDummyFileName = (format) => {
    switch (format.toLowerCase()) {
      case "word":
        return "dummy.docx";
      case "markup":
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
    alert(`Downloading ${getDummyFileName(format)}...`);
  };

  return (
    <div className={styles.page}>
      <motion.h1
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className={styles.title}
      >
        Generated Files
      </motion.h1>

  <div className={styles.fileList}>
  {formats.map((format, idx) => (
    <motion.div
      key={idx}
      className={styles.fileCard}
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: idx * 0.1 }}
    >
      {/* File Header */}
      <div className={styles.fileHeader}>
        <div className={styles.fileInfo}>
          {getFileIcon(format)}
          <span className={styles.fileName}>{getDummyFileName(format)}</span>
        </div>

        {/* Download Button */}
        <motion.button
          className={styles.downloadBtn}
          whileHover={{ scale: 1.1, rotate: 5 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => handleDownload(format)}
        >
          <Download size={20} />
        </motion.button>
      </div>

      {/* Preview */}
      <div className={styles.filePreview}>
  <pre>
    <code>
      {getTruncatedContent(format)}
    </code>
  </pre>
</div>
    </motion.div>
  ))}
</div>

    </div>
  );
}

import { motion } from "framer-motion";

export const Loader = () => {
  return (
    <motion.div
      className="ml-4 w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"
      initial={{ rotate: 0 }}
      animate={{ rotate: 360 }}
      transition={{ repeat: Infinity, duration: 1 }}
    />
  );
};

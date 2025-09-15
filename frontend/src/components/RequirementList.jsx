import { motion } from "framer-motion";

export default function RequirementList({ requirements, onGenerate }) {
  return (
    <motion.div
      className="bg-white p-6 rounded-xl shadow-md"
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <h2 className="text-xl font-semibold mb-4">Extracted Requirements</h2>
      <ul className="divide-y divide-gray-200">
        {requirements.map((req) => (
          <li key={req.id} className="py-3 flex items-center justify-between">
            <p className="text-gray-700">{req.text}</p>
            <button
              onClick={() => onGenerate(req.id)}
              className="bg-green-600 hover:bg-green-700 px-4 py-2 text-white rounded-lg transition"
            >
              Generate Tests
            </button>
          </li>
        ))}
      </ul>
    </motion.div>
  );
}

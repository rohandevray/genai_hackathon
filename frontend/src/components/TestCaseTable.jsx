import { approveTestCase } from "../api";

export default function TestCaseTable({ testCases }) {
  const handleApprove = async (testId) => {
    try {
      await approveTestCase(testId, { status: "approved" });
      alert("Test case approved!");
    } catch {
      alert("Approval failed!");
    }
  };

  return (
    <div className="bg-white mt-6 p-6 rounded-xl shadow-md">
      <h2 className="text-xl font-semibold mb-4">Generated Test Cases</h2>
      <table className="w-full border">
        <thead className="bg-gray-100">
          <tr>
            <th className="p-3 border">Test Case ID</th>
            <th className="p-3 border">Title</th>
            <th className="p-3 border">Steps</th>
            <th className="p-3 border">Expected Result</th>
            <th className="p-3 border">Action</th>
          </tr>
        </thead>
        <tbody>
          {testCases.map((tc) => (
            <tr key={tc.test_id} className="border-b hover:bg-gray-50">
              <td className="p-3 border">{tc.test_id}</td>
              <td className="p-3 border">{tc.title}</td>
              <td className="p-3 border">
                <ul className="list-disc pl-4">
                  {tc.steps.map((step, i) => (
                    <li key={i}>{step}</li>
                  ))}
                </ul>
              </td>
              <td className="p-3 border">{tc.expected_result}</td>
              <td className="p-3 border text-center">
                <button
                  onClick={() => handleApprove(tc.test_id)}
                  className="bg-blue-600 hover:bg-blue-700 px-4 py-2 text-white rounded-lg"
                >
                  Approve
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

"use client";

import type { BulkLintResult } from "@/lib/types";
import { Badge } from "@/components/shared/Badge";

interface LintResultsMatrixProps {
  data: BulkLintResult;
  onClose: () => void;
}

export function LintResultsMatrix({ data, onClose }: LintResultsMatrixProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[80vh] flex flex-col mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <div className="flex items-center gap-3">
            <h2 className="font-semibold text-sm">TESLint Results</h2>
            <span className="text-xs text-gray-400">
              {data.passed}/{data.total} passed
            </span>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg">&times;</button>
        </div>

        {/* Summary bar */}
        <div className="flex gap-4 px-4 py-2 bg-gray-50 border-b text-xs">
          <span className="text-green-600 font-medium">{data.passed} passed</span>
          <span className="text-red-600 font-medium">{data.failed} failed</span>
          <span className="text-gray-500">{data.total} total</span>
        </div>

        {/* Table */}
        <div className="overflow-auto flex-1">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 sticky top-0">
              <tr className="text-left text-xs text-gray-500">
                <th className="px-4 py-2 font-medium">Skill</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium text-center">Errors</th>
                <th className="px-4 py-2 font-medium text-center">Warnings</th>
                <th className="px-4 py-2 font-medium text-center">Result</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {data.results.map((r) => (
                <tr key={r.skill_name} className="hover:bg-gray-50">
                  <td className="px-4 py-2">
                    <span className="font-medium">{r.skill_name}</span>
                  </td>
                  <td className="px-4 py-2">
                    <Badge variant={r.status === "ACTIVE" ? "success" : "warning"}>
                      {r.status}
                    </Badge>
                  </td>
                  <td className="px-4 py-2 text-center">
                    {r.error_count > 0 ? (
                      <span className="text-red-600 font-medium">{r.error_count}</span>
                    ) : (
                      <span className="text-gray-300">0</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-center">
                    {r.warning_count > 0 ? (
                      <span className="text-yellow-600 font-medium">{r.warning_count}</span>
                    ) : (
                      <span className="text-gray-300">0</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-center">
                    {r.error_message ? (
                      <Badge variant="danger">ERROR</Badge>
                    ) : r.passed ? (
                      <Badge variant="success">PASS</Badge>
                    ) : (
                      <Badge variant="danger">FAIL</Badge>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

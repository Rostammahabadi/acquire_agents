"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { BusinessDetail, FollowUpQuestion } from "@/types";

export default function BusinessDetailPage() {
  const params = useParams();
  const businessId = params.business_id as string;

  const [business, setBusiness] = useState<BusinessDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [savingResponse, setSavingResponse] = useState<string | null>(null);
  const [triggerLoading, setTriggerLoading] = useState<string | null>(null);

  useEffect(() => {
    fetchBusinessDetail();
  }, [businessId]);

  const fetchBusinessDetail = async () => {
    try {
      const response = await fetch(`/api/businesses/${businessId}`);
      if (!response.ok) {
        throw new Error("Failed to fetch business detail");
      }
      const data = await response.json();
      setBusiness(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  const triggerAgentRun = async (endpoint: string, actionName: string) => {
    setTriggerLoading(actionName);
    try {
      const response = await fetch(`/api/run/${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ business_id: businessId }),
      });

      if (!response.ok) {
        throw new Error(`Failed to trigger ${actionName}`);
      }

      const result = await response.json();

      if (result.success) {
        alert(`${actionName} triggered successfully! Run ID: ${result.run_id}`);
      } else {
        alert(`${actionName} failed: ${result.message}`);
        return;
      }

      // Refresh the data after a short delay to show updated status
      setTimeout(() => {
        fetchBusinessDetail();
      }, 3000);
    } catch (err) {
      alert(
        `Error triggering ${actionName}: ${
          err instanceof Error ? err.message : "Unknown error"
        }`
      );
    } finally {
      setTriggerLoading(null);
    }
  };

  const triggerAllOperations = async () => {
    const actionName = "Run All";
    setTriggerLoading(actionName);

    try {
      // Trigger all three operations in parallel
      const [canonicalizeResponse, scoreResponse, followUpResponse] =
        await Promise.allSettled([
          fetch("/api/run/canonicalize", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ business_id: businessId }),
          }),
          fetch("/api/run/score", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ business_id: businessId }),
          }),
          fetch("/api/run/follow-ups", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ business_id: businessId }),
          }),
        ]);

      const results = [];

      // Check canonicalization result
      if (canonicalizeResponse.status === "fulfilled") {
        const canonicalizeResult = await canonicalizeResponse.value.json();
        if (canonicalizeResult.success) {
          results.push(`Canonicalization: Run ID ${canonicalizeResult.run_id}`);
        } else {
          results.push(
            `Canonicalization failed: ${canonicalizeResult.message}`
          );
        }
      } else {
        results.push(`Canonicalization error: ${canonicalizeResponse.reason}`);
      }

      // Check scoring result
      if (scoreResponse.status === "fulfilled") {
        const scoreResult = await scoreResponse.value.json();
        if (scoreResult.success) {
          results.push(`Scoring: Run ID ${scoreResult.run_id}`);
        } else {
          results.push(`Scoring failed: ${scoreResult.message}`);
        }
      } else {
        results.push(`Scoring error: ${scoreResponse.reason}`);
      }

      // Check follow-up result
      if (followUpResponse.status === "fulfilled") {
        const followUpResult = await followUpResponse.value.json();
        if (followUpResult.success) {
          results.push(`Follow-ups: Run ID ${followUpResult.run_id}`);
        } else {
          results.push(`Follow-ups failed: ${followUpResult.message}`);
        }
      } else {
        results.push(`Follow-ups error: ${followUpResponse.reason}`);
      }

      // Show results
      alert(`Operations completed:\n${results.join("\n")}`);

      // Refresh the data after a short delay
      setTimeout(() => {
        fetchBusinessDetail();
      }, 3000);
    } catch (err) {
      alert(
        `Error triggering all operations: ${
          err instanceof Error ? err.message : "Unknown error"
        }`
      );
    } finally {
      setTriggerLoading(null);
    }
  };

  const triggerScoringAndFollowUps = async () => {
    const actionName = "Scoring & Follow-ups";
    setTriggerLoading(actionName);

    try {
      // First, trigger scoring
      const scoringResponse = await fetch("/api/run/score", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ business_id: businessId }),
      });

      if (!scoringResponse.ok) {
        throw new Error("Failed to trigger scoring");
      }

      const scoringResult = await scoringResponse.json();

      if (!scoringResult.success) {
        alert(`Scoring failed: ${scoringResult.message}`);
        return;
      }

      alert(`Scoring triggered successfully! Run ID: ${scoringResult.run_id}`);

      // Wait a bit for scoring to complete, then fetch updated business data
      setTimeout(async () => {
        await fetchBusinessDetail();

        // Check if we have a scoring record and if it's tier A or B
        const updatedBusiness = await fetch(
          `/api/businesses/${businessId}`
        ).then((r) => r.json());

        if (
          updatedBusiness.scoring_record &&
          (updatedBusiness.scoring_record.tier === "A" ||
            updatedBusiness.scoring_record.tier === "B")
        ) {
          // Automatically trigger follow-up generation for A/B tier businesses
          const followUpResponse = await fetch("/api/run/follow-ups", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ business_id: businessId }),
          });

          if (!followUpResponse.ok) {
            throw new Error("Failed to trigger follow-up generation");
          }

          const followUpResult = await followUpResponse.json();

          if (followUpResult.success) {
            alert(
              `Follow-up generation triggered successfully! Run ID: ${followUpResult.run_id}`
            );
          } else {
            alert(`Follow-up generation failed: ${followUpResult.message}`);
          }
        } else if (updatedBusiness.scoring_record) {
          alert(
            `Business scored as Tier ${updatedBusiness.scoring_record.tier}. Follow-up generation is only available for Tier A and B businesses.`
          );
        }

        // Final refresh to show all updated data
        setTimeout(() => {
          fetchBusinessDetail();
        }, 3000);
      }, 5000); // Wait 5 seconds for scoring to complete
    } catch (err) {
      alert(
        `Error triggering scoring and follow-ups: ${
          err instanceof Error ? err.message : "Unknown error"
        }`
      );
    } finally {
      setTriggerLoading(null);
    }
  };

  const saveResponse = async (questionId: string) => {
    const response = responses[questionId];
    if (!response?.trim()) {
      alert("Please enter a response");
      return;
    }

    setSavingResponse(questionId);
    try {
      const result = await fetch("/api/follow-ups/respond", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question_id: questionId,
          response: response.trim(),
        }),
      });

      if (!result.ok) {
        throw new Error("Failed to save response");
      }

      alert("Response saved successfully!");
      setResponses((prev) => ({ ...prev, [questionId]: "" }));

      // Refresh the data
      fetchBusinessDetail();
    } catch (err) {
      alert(
        `Error saving response: ${
          err instanceof Error ? err.message : "Unknown error"
        }`
      );
    } finally {
      setSavingResponse(null);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical":
        return "text-red-600 bg-red-100";
      case "high":
        return "text-orange-600 bg-orange-100";
      case "medium":
        return "text-yellow-600 bg-yellow-100";
      case "low":
        return "text-green-600 bg-green-100";
      default:
        return "text-gray-600 bg-gray-100";
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "responded":
        return "text-green-600 bg-green-100";
      case "pending":
        return "text-yellow-600 bg-yellow-100";
      case "no_response":
        return "text-red-600 bg-red-100";
      case "escalated":
        return "text-purple-600 bg-purple-100";
      default:
        return "text-gray-600 bg-gray-100";
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !business) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="flex">
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">
              Error loading business details
            </h3>
            <div className="mt-2 text-sm text-red-700">
              {error || "Business not found"}
            </div>
            <div className="mt-4">
              <Link
                href="/businesses"
                className="text-sm text-red-600 hover:text-red-500"
              >
                ← Back to businesses
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold text-gray-900">
              Business Details
            </h2>
            <p className="mt-2 text-gray-600 font-mono text-sm">
              {business.business_id}
            </p>
          </div>
          <Link
            href="/businesses"
            className="text-blue-600 hover:text-blue-900"
          >
            ← Back to businesses
          </Link>
        </div>
      </div>

      <div className="space-y-8">
        {/* Raw Listing Section */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900">Raw Listing</h3>
              <div className="flex space-x-3">
                <button
                  onClick={() =>
                    triggerAgentRun("canonicalize", "Canonicalization")
                  }
                  disabled={triggerLoading === "Canonicalization"}
                  className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {triggerLoading === "Canonicalization"
                    ? "Running..."
                    : "Re-run Canonicalization"}
                </button>
                <button
                  onClick={triggerAllOperations}
                  disabled={triggerLoading === "Run All"}
                  className="px-4 py-2 bg-purple-600 text-white text-sm rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {triggerLoading === "Run All" ? "Running All..." : "Run All"}
                </button>
              </div>
            </div>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Listing URL
                </label>
                <a
                  href={business.raw_listing.listing_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-900 break-all"
                >
                  {business.raw_listing.listing_url}
                </a>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Scrape Timestamp
                </label>
                <p className="text-sm text-gray-900">
                  {new Date(
                    business.raw_listing.scrape_timestamp
                  ).toLocaleString()}
                </p>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Raw Text
              </label>
              <div className="bg-gray-50 border rounded-md p-4 max-h-60 overflow-y-auto">
                <pre className="text-sm text-gray-800 whitespace-pre-wrap">
                  {business.raw_listing.raw_text}
                </pre>
              </div>
            </div>
          </div>
        </div>

        {/* Canonical Business Record Section */}
        {business.canonical_record && (
          <div className="bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium text-gray-900">
                  Canonical Business Record
                </h3>
                <button
                  onClick={triggerScoringAndFollowUps}
                  disabled={triggerLoading === "Scoring & Follow-ups"}
                  className="px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {triggerLoading === "Scoring & Follow-ups"
                    ? "Generating Scoring & Follow-ups..."
                    : "Generate Scoring & Follow-ups"}
                </button>
              </div>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {business.canonical_record.financials && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">
                      Financials
                    </h4>
                    <pre className="text-xs text-gray-600 bg-gray-50 p-2 rounded overflow-x-auto">
                      {JSON.stringify(
                        business.canonical_record.financials,
                        null,
                        2
                      )}
                    </pre>
                  </div>
                )}
                {business.canonical_record.product && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">Product</h4>
                    <pre className="text-xs text-gray-600 bg-gray-50 p-2 rounded overflow-x-auto">
                      {JSON.stringify(
                        business.canonical_record.product,
                        null,
                        2
                      )}
                    </pre>
                  </div>
                )}
                {business.canonical_record.customers && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">
                      Customers
                    </h4>
                    <pre className="text-xs text-gray-600 bg-gray-50 p-2 rounded overflow-x-auto">
                      {JSON.stringify(
                        business.canonical_record.customers,
                        null,
                        2
                      )}
                    </pre>
                  </div>
                )}
                {business.canonical_record.operations && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">
                      Operations
                    </h4>
                    <pre className="text-xs text-gray-600 bg-gray-50 p-2 rounded overflow-x-auto">
                      {JSON.stringify(
                        business.canonical_record.operations,
                        null,
                        2
                      )}
                    </pre>
                  </div>
                )}
                {business.canonical_record.technology && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">
                      Technology
                    </h4>
                    <pre className="text-xs text-gray-600 bg-gray-50 p-2 rounded overflow-x-auto">
                      {JSON.stringify(
                        business.canonical_record.technology,
                        null,
                        2
                      )}
                    </pre>
                  </div>
                )}
                {business.canonical_record.growth && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">Growth</h4>
                    <pre className="text-xs text-gray-600 bg-gray-50 p-2 rounded overflow-x-auto">
                      {JSON.stringify(
                        business.canonical_record.growth,
                        null,
                        2
                      )}
                    </pre>
                  </div>
                )}
                {business.canonical_record.risks && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">Risks</h4>
                    <pre className="text-xs text-gray-600 bg-gray-50 p-2 rounded overflow-x-auto">
                      {JSON.stringify(business.canonical_record.risks, null, 2)}
                    </pre>
                  </div>
                )}
                {business.canonical_record.seller && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">Seller</h4>
                    <pre className="text-xs text-gray-600 bg-gray-50 p-2 rounded overflow-x-auto">
                      {JSON.stringify(
                        business.canonical_record.seller,
                        null,
                        2
                      )}
                    </pre>
                  </div>
                )}
                {business.canonical_record.confidence_flags && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">
                      Confidence Flags
                    </h4>
                    <pre className="text-xs text-gray-600 bg-gray-50 p-2 rounded overflow-x-auto">
                      {JSON.stringify(
                        business.canonical_record.confidence_flags,
                        null,
                        2
                      )}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Scoring Section */}
        {business.scoring_record && (
          <div className="bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium text-gray-900">Scoring</h3>
                {business.scoring_record.tier === "A" ||
                business.scoring_record.tier === "B" ? (
                  <button
                    onClick={() =>
                      triggerAgentRun("follow-ups", "Follow-up Generation")
                    }
                    disabled={triggerLoading === "Follow-up Generation"}
                    className="px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {triggerLoading === "Follow-up Generation"
                      ? "Generating..."
                      : "Generate Follow-Up Questions"}
                  </button>
                ) : (
                  <span className="text-sm text-gray-500">
                    Tier {business.scoring_record.tier} - Follow-ups disabled
                  </span>
                )}
              </div>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                <div className="text-center">
                  <div className="text-3xl font-bold text-gray-900">
                    {business.scoring_record.total_score.toFixed(1)}
                  </div>
                  <div className="text-sm text-gray-600">Total Score</div>
                </div>
                <div className="text-center">
                  <div
                    className={`text-3xl font-bold ${
                      business.scoring_record.tier === "A"
                        ? "text-green-600"
                        : business.scoring_record.tier === "B"
                        ? "text-blue-600"
                        : business.scoring_record.tier === "C"
                        ? "text-yellow-600"
                        : "text-red-600"
                    }`}
                  >
                    {business.scoring_record.tier}
                  </div>
                  <div className="text-sm text-gray-600">Tier</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-gray-900">
                    {business.scoring_record.scoring_timestamp.split("T")[0]}
                  </div>
                  <div className="text-sm text-gray-600">Scored On</div>
                </div>
              </div>

              <div className="mb-6">
                <h4 className="font-medium text-gray-900 mb-3">
                  Component Scores
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                    <span className="text-sm text-gray-600">
                      Price Efficiency
                    </span>
                    <span className="font-medium">
                      {business.scoring_record.price_efficiency_score}
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                    <span className="text-sm text-gray-600">
                      Revenue Quality
                    </span>
                    <span className="font-medium">
                      {business.scoring_record.revenue_quality_score}
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                    <span className="text-sm text-gray-600">Moat</span>
                    <span className="font-medium">
                      {business.scoring_record.moat_score}
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                    <span className="text-sm text-gray-600">AI Leverage</span>
                    <span className="font-medium">
                      {business.scoring_record.ai_leverage_score}
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                    <span className="text-sm text-gray-600">Operations</span>
                    <span className="font-medium">
                      {business.scoring_record.operations_score}
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                    <span className="text-sm text-gray-600">Risk</span>
                    <span className="font-medium">
                      {business.scoring_record.risk_score}
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                    <span className="text-sm text-gray-600">Trust</span>
                    <span className="font-medium">
                      {business.scoring_record.trust_score}
                    </span>
                  </div>
                </div>
              </div>

              <div className="mb-6">
                <h4 className="font-medium text-gray-900 mb-3">
                  Top Buy Reasons
                </h4>
                <ul className="list-disc list-inside space-y-1">
                  {business.scoring_record.top_buy_reasons.map(
                    (reason, index) => (
                      <li key={index} className="text-sm text-gray-700">
                        {reason}
                      </li>
                    )
                  )}
                </ul>
              </div>

              <div>
                <h4 className="font-medium text-gray-900 mb-3">Top Risks</h4>
                <ul className="list-disc list-inside space-y-1">
                  {business.scoring_record.top_risks.map((risk, index) => (
                    <li key={index} className="text-sm text-gray-700">
                      {risk}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Follow-Up Questions Section */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">
              Follow-Up Questions
            </h3>
          </div>
          <div className="p-6">
            {business.follow_up_questions.length === 0 ? (
              <p className="text-gray-500">
                No follow-up questions generated yet.
              </p>
            ) : (
              <div className="space-y-6">
                {business.follow_up_questions.map((question) => (
                  <div
                    key={question.id}
                    className="border border-gray-200 rounded-lg p-4"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <p className="text-sm text-gray-900 mb-2">
                          {question.question_text}
                        </p>
                        <div className="flex items-center space-x-4 text-xs">
                          <span
                            className={`px-2 py-1 rounded-full font-medium ${getSeverityColor(
                              question.severity
                            )}`}
                          >
                            {question.severity}
                          </span>
                          <span
                            className={`px-2 py-1 rounded-full font-medium ${getStatusColor(
                              question.response_status
                            )}`}
                          >
                            {question.response_status}
                          </span>
                          <span className="text-gray-500">
                            Triggered by: {question.triggered_by_field}
                          </span>
                        </div>
                      </div>
                    </div>

                    {question.response_status === "pending" && (
                      <div className="mt-4">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Seller Response
                        </label>
                        <textarea
                          value={responses[question.id] || ""}
                          onChange={(e) =>
                            setResponses((prev) => ({
                              ...prev,
                              [question.id]: e.target.value,
                            }))
                          }
                          placeholder="Paste the seller's response here..."
                          rows={3}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        />
                        <div className="mt-2 flex justify-end">
                          <button
                            onClick={() => saveResponse(question.id)}
                            disabled={savingResponse === question.id}
                            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {savingResponse === question.id
                              ? "Saving..."
                              : "Save Response"}
                          </button>
                        </div>
                      </div>
                    )}

                    {question.seller_response && (
                      <div className="mt-4">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Seller Response (
                          {question.response_timestamp
                            ? new Date(
                                question.response_timestamp
                              ).toLocaleString()
                            : "Unknown time"}
                          )
                        </label>
                        <div className="bg-gray-50 border rounded-md p-3">
                          <p className="text-sm text-gray-900 whitespace-pre-wrap">
                            {question.seller_response}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

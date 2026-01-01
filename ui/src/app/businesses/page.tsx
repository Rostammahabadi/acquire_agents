"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BusinessListing } from "@/types";

export default function BusinessesPage() {
  const [businesses, setBusinesses] = useState<BusinessListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [runAllLoading, setRunAllLoading] = useState(false);
  const [scrapingLoading, setScrapingLoading] = useState(false);
  const [tierFilter, setTierFilter] = useState<string>("all");

  useEffect(() => {
    fetchBusinesses();
  }, [tierFilter]);

  const fetchBusinesses = async () => {
    try {
      const url =
        tierFilter === "all"
          ? "/api/businesses"
          : `/api/businesses?tier=${tierFilter}`;
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error("Failed to fetch businesses");
      }
      const data = await response.json();
      setBusinesses(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  const scrapeListings = async () => {
    setScrapingLoading(true);

    try {
      const response = await fetch("/api/scrape", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to scrape listings");
      }

      const result = await response.json();

      // Show results
      const summary = `Scraping completed!\n\n${result.message}\n\nStats:\n- URLs found: ${result.stats.total_urls_found}\n- Already exist: ${result.stats.already_exist}\n- Newly scraped: ${result.stats.scraped}\n- Failed: ${result.stats.failed}\n- Inserted: ${result.stats.inserted}`;
      alert(summary);

      // Refresh the business list
      await fetchBusinesses();
    } catch (err) {
      alert(
        `Error scraping listings: ${
          err instanceof Error ? err.message : "Unknown error"
        }`
      );
    } finally {
      setScrapingLoading(false);
    }
  };

  const runAllOperations = async () => {
    if (businesses.length === 0) {
      alert("No businesses found to process.");
      return;
    }

    setRunAllLoading(true);

    try {
      const results = [];
      let successCount = 0;
      let errorCount = 0;

      // Process each business sequentially to avoid overwhelming the backend
      for (const business of businesses) {
        const businessId = business.business_id;
        const operations = [];

        try {
          // Check which operations are needed based on pipeline status
          const operations: string[] = [];
          if (!business.pipeline_status.canonicalized) {
            operations.push("canonicalize");
          }
          if (!business.pipeline_status.scored) {
            operations.push("score");
          }
          if (
            !business.pipeline_status.follow_up_generated &&
            business.pipeline_status.scored &&
            (business.latest_tier === "A" || business.latest_tier === "B")
          ) {
            operations.push("follow-ups");
          }

          if (operations.length === 0) {
            results.push(`${businessId.slice(0, 8)}...: Already processed`);
            successCount++;
            continue;
          }

          // Run operations in parallel for this business
          const operationPromises = operations.map(async (operation) => {
            const response = await fetch(`/api/run/${operation}`, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({ business_id: businessId }),
            });

            if (!response.ok) {
              throw new Error(`${operation} failed`);
            }

            const result = await response.json();
            return { operation, result };
          });

          const operationResults = await Promise.allSettled(operationPromises);

          const businessResults = operationResults.map((result, index) => {
            const operation = operations[index];
            if (result.status === "fulfilled") {
              return `${operation}: ✓ (Run ID: ${result.value.result.run_id})`;
            } else {
              errorCount++;
              return `${operation}: ✗ (${result.reason.message})`;
            }
          });

          results.push(
            `${businessId.slice(0, 8)}...: ${businessResults.join(", ")}`
          );
          if (operationResults.every((r) => r.status === "fulfilled")) {
            successCount++;
          } else {
            errorCount++;
          }
        } catch (err) {
          results.push(
            `${businessId.slice(0, 8)}...: ✗ Error: ${
              err instanceof Error ? err.message : "Unknown error"
            }`
          );
          errorCount++;
        }
      }

      // Show summary
      const summary = `Processing complete!\n\nSuccessful: ${successCount}\nErrors: ${errorCount}\n\nDetails:\n${results.join(
        "\n"
      )}`;
      alert(summary);

      // Refresh the business list
      await fetchBusinesses();
    } catch (err) {
      alert(
        `Error running operations: ${
          err instanceof Error ? err.message : "Unknown error"
        }`
      );
    } finally {
      setRunAllLoading(false);
    }
  };

  const getStatusBadge = (status: boolean, label: string) => (
    <span
      className={`px-2 py-1 text-xs rounded-full ${
        status ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-600"
      }`}
    >
      {label}
    </span>
  );

  const getTierBadge = (tier?: string) => {
    if (!tier) return <span className="text-gray-500">unscored</span>;

    const colors = {
      A: "bg-green-100 text-green-800",
      B: "bg-blue-100 text-blue-800",
      C: "bg-yellow-100 text-yellow-800",
      D: "bg-red-100 text-red-800",
    };

    return (
      <span
        className={`px-2 py-1 text-xs font-medium rounded-full ${
          colors[tier as keyof typeof colors]
        }`}
      >
        {tier}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="flex">
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">
              Error loading businesses
            </h3>
            <div className="mt-2 text-sm text-red-700">{error}</div>
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
              Business Pipeline
            </h2>
            <p className="mt-2 text-gray-600">
              View and manage businesses in the acquisition pipeline.
            </p>
          </div>
          <div className="flex space-x-4">
            <button
              onClick={scrapeListings}
              disabled={scrapingLoading}
              className="px-6 py-3 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {scrapingLoading ? "Scraping..." : "Scrape New Listings"}
            </button>
            <button
              onClick={runAllOperations}
              disabled={runAllLoading}
              className="px-6 py-3 bg-purple-600 text-white text-sm font-medium rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {runAllLoading ? "Processing All..." : "Run All Operations"}
            </button>
          </div>
        </div>

        {/* Tier Filter Controls */}
        <div className="mt-6">
          <div className="flex items-center space-x-4">
            <label
              htmlFor="tier-filter"
              className="text-sm font-medium text-gray-700"
            >
              Filter by Tier:
            </label>
            <select
              id="tier-filter"
              value={tierFilter}
              onChange={(e) => setTierFilter(e.target.value)}
              className="block w-32 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
            >
              <option value="all">All Tiers</option>
              <option value="A">Tier A</option>
              <option value="B">Tier B</option>
              <option value="C">Tier C</option>
              <option value="D">Tier D</option>
            </select>
            {tierFilter !== "all" && (
              <span className="text-sm text-gray-500">
                Showing {businesses.length} {tierFilter} tier businesses
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Business ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Marketplace
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Asking Price
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Latest Tier
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Total Score
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Pipeline Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {businesses.map((business) => (
                <tr key={business.business_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                    {business.business_id.slice(0, 8)}...
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {business.marketplace}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {business.asking_price
                      ? `$${business.asking_price.toLocaleString()}`
                      : "-"}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {getTierBadge(business.latest_tier)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {business.latest_total_score?.toFixed(1) || "-"}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex flex-wrap gap-1">
                      {getStatusBadge(
                        business.pipeline_status.scraped,
                        "scraped"
                      )}
                      {getStatusBadge(
                        business.pipeline_status.canonicalized,
                        "canonicalized"
                      )}
                      {getStatusBadge(
                        business.pipeline_status.scored,
                        "scored"
                      )}
                      {getStatusBadge(
                        business.pipeline_status.follow_up_generated,
                        "follow-ups"
                      )}
                      {getStatusBadge(
                        business.pipeline_status.awaiting_response,
                        "awaiting"
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <Link
                      href={`/businesses/${business.business_id}`}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      View Details →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {businesses.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500">
              No businesses found in the pipeline.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

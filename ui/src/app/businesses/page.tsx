"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BusinessListing } from "@/types";

export default function BusinessesPage() {
  const [businesses, setBusinesses] = useState<BusinessListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchBusinesses();
  }, []);

  const fetchBusinesses = async () => {
    try {
      const response = await fetch("/api/businesses");
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
        <h2 className="text-3xl font-bold text-gray-900">Business Pipeline</h2>
        <p className="mt-2 text-gray-600">
          View and manage businesses in the acquisition pipeline.
        </p>
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

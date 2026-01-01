import { NextResponse } from "next/server";
import { getBusinessDetail } from "@/lib/database";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ business_id: string }> }
) {
  try {
    const { business_id: businessId } = await params;
    const businessDetail = await getBusinessDetail(businessId);
    return NextResponse.json(businessDetail);
  } catch (error) {
    console.error("Error fetching business detail:", error);
    if (error instanceof Error && error.message === "Business not found") {
      return NextResponse.json(
        { error: "Business not found" },
        { status: 404 }
      );
    }
    return NextResponse.json(
      { error: "Failed to fetch business detail" },
      { status: 500 }
    );
  }
}

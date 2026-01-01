import { NextResponse } from "next/server";
import { saveFollowUpResponse } from "@/lib/database";

export async function POST(request: Request) {
  try {
    const { question_id, response } = await request.json();

    if (!question_id || !response) {
      return NextResponse.json(
        { error: "question_id and response are required" },
        { status: 400 }
      );
    }

    const result = await saveFollowUpResponse(question_id, response);
    return NextResponse.json(result);
  } catch (error) {
    console.error("Error saving response:", error);
    return NextResponse.json(
      { error: "Failed to save response" },
      { status: 500 }
    );
  }
}

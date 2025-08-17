"use client";
import Chatbot from "@/components/Chatbot";
import ProtectedRoute from "@/components/ProtectedRoute";

export default function ChatPage() {

  return (
    <ProtectedRoute>
      <div className="h-screen w-full">
        <Chatbot />
      </div>
    </ProtectedRoute>
  );
}
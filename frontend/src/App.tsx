import { ChatWindow } from "./components/ChatWindow";
import { Sidebar } from "./components/Sidebar";

export default function App(): JSX.Element {
  // TODO: wire session state
  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      <Sidebar />
      <main className="flex-1 flex flex-col">
        <ChatWindow />
      </main>
    </div>
  );
}

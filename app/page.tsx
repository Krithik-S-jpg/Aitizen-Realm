import { requireChatGPTUser } from "./chatgpt-auth";
import Observatory from "./observatory";
export const dynamic="force-dynamic";
export default async function Home(){await requireChatGPTUser("/");return <Observatory/>;}

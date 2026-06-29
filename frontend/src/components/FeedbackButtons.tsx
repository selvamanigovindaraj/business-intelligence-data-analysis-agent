import { useFeedback } from "../hooks/useFeedback";

interface Props {
  sessionId: string;
  messageId: string;
}

export function FeedbackButtons({ sessionId, messageId }: Props): JSX.Element {
  const { giveFeedback } = useFeedback(sessionId);
  // TODO: implement thumbs-up/down UI with optimistic state
  return <></>;
}

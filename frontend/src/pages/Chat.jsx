import { useParams } from "react-router-dom";

export default function Chat() {
  const { roomId } = useParams();

  return (
    <section>
      <h1 className="text-2xl font-bold">Phòng chat</h1>
      <p className="mt-2 text-slate-600">
        Giao diện chat sẽ được bổ sung ở task sau. Mã phòng: {roomId}
      </p>
    </section>
  );
}

import { Radar } from "lucide-react";
import { Link } from "react-router-dom";
import { EmptyState } from "@/components/EmptyState";

export function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <EmptyState
        icon={Radar}
        title="Esta ruta no está en el radar"
        description="La página que buscas no existe o cambió de lugar. Vuelve al dashboard para seguir explorando oportunidades."
        action={
          <Link to="/" className="btn-primary">
            Volver al dashboard
          </Link>
        }
      />
    </div>
  );
}

import { useQuery } from '@tanstack/react-query';
import { getMetricsSummary, getMetricsHistory, getAlerts } from '../api/metrics';

export function useMetrics() {
    const summary = useQuery({ queryKey: ['metricsSummary'], queryFn: getMetricsSummary, refetchInterval: 30000 });
    const history = useQuery({ queryKey: ['metricsHistory'], queryFn: () => getMetricsHistory(7), refetchInterval: 30000 });
    const alerts = useQuery({ queryKey: ['metricsAlerts'], queryFn: getAlerts, refetchInterval: 30000 });

    return { summary, history, alerts };
}

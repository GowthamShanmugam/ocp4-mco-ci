import * as React from 'react';
import { useCustomPrometheusPoll } from '@odf/shared/hooks/custom-prometheus-poll';
import { useK8sWatchResources } from '@openshift-console/dynamic-plugin-sdk';
import { ACMManagedClusterKind, DRClusterAppsMap } from 'packages/mco/types';
import { Grid, GridItem } from '@patternfly/react-core';
import { ACM_ENDPOINT, HUB_CLUSTER_NAME } from '../../../constants';
import {
  getManagedClusterResourceObj,
  useDisasterRecoveryResourceWatch,
} from '../../../hooks';
import { StorageDashboard, STATUS_QUERIES } from '../queries';
import { AlertsCard } from './alert-card/alert-card';
import { ClusterAppCard } from './cluster-app-card/cluster-app-card';
import { CSVStatusesContext, DRResourcesContext } from './dr-dashboard-context';
import { useApplicationSetParser } from './parsers/applicationset-parser';
import { useSubscriptionParser } from './parsers/subscription-parser';
import { StatusCard } from './status-card/status-card';
import { SummaryCard } from './summary-card/summary-card';
import '../mco-dashboard.scss';
import '../../../style.scss';

const UpperSection: React.FC = () => (
  <Grid hasGutter>
    <GridItem lg={8} rowSpan={3} sm={12}>
      <StatusCard />
    </GridItem>
    <GridItem lg={4} rowSpan={6} sm={12}>
      <AlertsCard />
    </GridItem>
    <GridItem lg={8} rowSpan={3} sm={12}>
      <SummaryCard />
    </GridItem>
    <GridItem lg={12} rowSpan={6} sm={12}>
      <ClusterAppCard />
    </GridItem>
  </Grid>
);

const aggregateApplicationData = (
  clusterAppsList: DRClusterAppsMap[]
): DRClusterAppsMap =>
  clusterAppsList.reduce((acc, clusterAppsMap) => {
    Object.keys(clusterAppsMap).forEach((clusterName) => {
      const { managedCluster, totalAppCount, protectedApps } =
        clusterAppsMap[clusterName];

      if (!acc.hasOwnProperty(clusterName)) {
        acc[clusterName] = {
          managedCluster: managedCluster,
          totalAppCount: totalAppCount,
          protectedApps: protectedApps,
        };
      } else {
        acc[clusterName].totalAppCount += totalAppCount;
        acc[clusterName].protectedApps =
          acc[clusterName].protectedApps.concat(protectedApps);
      }
    });
    return acc;
  }, {});

const DRDashboard: React.FC = () => {
  const [csvData, csvError, csvLoading] = useCustomPrometheusPoll({
    endpoint: 'api/v1/query' as any,
    query: STATUS_QUERIES[StorageDashboard.CSV_STATUS_ALL_WHITELISTED],
    basePath: ACM_ENDPOINT,
    cluster: HUB_CLUSTER_NAME,
  });

  const [drResources, drLoaded, drLoadError] =
    useDisasterRecoveryResourceWatch();

  const managedClusterResponse = useK8sWatchResources<{
    managedClusters: ACMManagedClusterKind[];
  }>({
    managedClusters: getManagedClusterResourceObj(),
  }).managedClusters;

  const [subscriptionData, subscriptionDataLoaded, subscriptionDataLoadError] =
    useSubscriptionParser(
      drResources,
      managedClusterResponse,
      drLoaded,
      drLoadError
    );

  const [
    applicationSetData,
    applicationSetDataLoaded,
    applicationSetDataLoadError,
  ] = useApplicationSetParser(
    drResources,
    managedClusterResponse,
    drLoaded,
    drLoadError
  );

  const [drClusterAppsMap, setDrClusterAppsMap] =
    React.useState<DRClusterAppsMap>({});

  const loaded = applicationSetDataLoaded && subscriptionDataLoaded;
  const loadError = applicationSetDataLoadError || subscriptionDataLoadError;

  React.useEffect(() => {
    if (subscriptionData && applicationSetData && !!loaded && !loadError) {
      const aggregatedData = aggregateApplicationData([
        subscriptionData,
        applicationSetData,
        // Add new application parser data
      ]);

      setDrClusterAppsMap(aggregatedData);
    }
  }, [subscriptionData, applicationSetData, loaded, loadError]);

  const dRResourcesContext = {
    drClusterAppsMap,
    loaded,
    loadError,
  };

  return (
    <div className="odf-dashboard-body">
      <CSVStatusesContext.Provider value={{ csvData, csvError, csvLoading }}>
        <DRResourcesContext.Provider value={dRResourcesContext}>
          <UpperSection />
        </DRResourcesContext.Provider>
      </CSVStatusesContext.Provider>
    </div>
  );
};

export default DRDashboard;

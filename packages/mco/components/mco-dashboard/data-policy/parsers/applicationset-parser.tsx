import * as React from 'react';
import { APPLICATION_TYPE, DRPC_STATUS } from '@odf/mco/constants';
import {
  DisasterRecoveryResourceKind,
  useArgoApplicationSetResourceWatch,
} from '@odf/mco/hooks';
import {
  ACMManagedClusterKind,
  DRClusterAppsMap,
  DRClusterKind,
} from '@odf/mco/types';
import {
  findDRType,
  findDeploymentClusters,
  getProtectedPVCsFromDRPC,
  getRemoteNamespaceFromAppSet,
} from '@odf/mco/utils';
import { getName, getNamespace } from '@odf/shared/selectors';
import { WatchK8sResultsObject } from '@openshift-console/dynamic-plugin-sdk';
import * as _ from 'lodash-es';

export const useApplicationSetParser = (
  drResources: DisasterRecoveryResourceKind,
  managedClusters: WatchK8sResultsObject<ACMManagedClusterKind>,
  drLoaded: boolean,
  drLoadError: any
): [DRClusterAppsMap, boolean, any] => {
  const [argoApplicationSetResources, loaded, loadError] =
    useArgoApplicationSetResourceWatch({
      overrides: { managedClusters: managedClusters },
      drResources: {
        data: drResources,
        loaded: drLoaded,
        loadError: drLoadError,
      },
    });

  const drClusters: DRClusterKind[] = drResources?.drClusters;
  const formattedArgoAppSetResources =
    argoApplicationSetResources?.formattedResources;

  const drClusterAppsMap: DRClusterAppsMap = React.useMemo(() => {
    if (loaded && !loadError) {
      const managedClusterList = Array.isArray(managedClusters.data)
        ? managedClusters.data
        : [managedClusters.data];
      // DRCluster to its ManagedCluster mapping
      const drClusterAppsMap: DRClusterAppsMap = drClusters.reduce(
        (acc, drCluster) => {
          const clusterName = getName(drCluster);
          acc[clusterName] = {
            managedCluster: managedClusterList.find(
              (managedCluster) => getName(managedCluster) === clusterName
            ),
            totalAppCount: 0,
            protectedApps: [],
          };
          return acc;
        },
        {} as DRClusterAppsMap
      );

      // DRCluster to its ApplicationSets (total and protected) mapping
      formattedArgoAppSetResources.forEach((argoApplicationSetResource) => {
        const { application } = argoApplicationSetResource || {};
        const {
          drClusters: currentDrClusters,
          drPlacementControl,
          drPolicy,
          placementDecision,
        } = argoApplicationSetResource?.placements?.[0] || {};
        const deploymentClusters = findDeploymentClusters(
          placementDecision,
          drPlacementControl
        );
        deploymentClusters.forEach((decisionCluster) => {
          if (drClusterAppsMap.hasOwnProperty(decisionCluster)) {
            drClusterAppsMap[decisionCluster].totalAppCount =
              drClusterAppsMap[decisionCluster].totalAppCount + 1;
            if (!_.isEmpty(drPlacementControl)) {
              drClusterAppsMap[decisionCluster].protectedApps.push({
                appName: getName(application),
                appNamespace: getNamespace(application),
                appKind: application?.kind,
                appAPIVersion: application?.apiVersion,
                appType: APPLICATION_TYPE.APPSET,
                placementInfo: [
                  {
                    deploymentClusterName: decisionCluster,
                    drpcName: getName(drPlacementControl),
                    drpcNamespace: getNamespace(drPlacementControl),
                    protectedPVCs: getProtectedPVCsFromDRPC(drPlacementControl),
                    replicationType: findDRType(currentDrClusters),
                    syncInterval: drPolicy?.spec?.schedulingInterval,
                    workloadNamespace:
                      getRemoteNamespaceFromAppSet(application),
                    failoverCluster: drPlacementControl?.spec?.failoverCluster,
                    preferredCluster:
                      drPlacementControl?.spec?.preferredCluster,
                    lastGroupSyncTime:
                      drPlacementControl?.status?.lastGroupSyncTime,
                    status: drPlacementControl?.status?.phase as DRPC_STATUS,
                  },
                ],
              });
            }
          }
        });
      });
      return drClusterAppsMap;
    }
    return {};
  }, [
    drClusters,
    formattedArgoAppSetResources,
    managedClusters.data,
    loaded,
    loadError,
  ]);

  return [drClusterAppsMap, loaded, loadError];
};

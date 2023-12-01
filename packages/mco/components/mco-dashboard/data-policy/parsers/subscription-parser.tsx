import * as React from 'react';
import { APPLICATION_TYPE, DRPC_STATUS } from '@odf/mco/constants';
import {
  DisasterRecoveryResourceKind,
  useSubscriptionResourceWatch,
} from '@odf/mco/hooks';
import {
  ACMManagedClusterKind,
  DRClusterAppsMap,
  DRClusterKind,
} from '@odf/mco/types';
import {
  findDRType,
  findDeploymentClusters,
  getAppUniqueId,
  getProtectedPVCsFromDRPC,
} from '@odf/mco/utils';
import { getName, getNamespace } from '@odf/shared/selectors';
import { WatchK8sResultsObject } from '@openshift-console/dynamic-plugin-sdk';
import * as _ from 'lodash-es';

export const useSubscriptionParser = (
  drResources: DisasterRecoveryResourceKind,
  managedClusters: WatchK8sResultsObject<ACMManagedClusterKind>,
  drLoaded: boolean,
  drLoadError: any
): [DRClusterAppsMap, boolean, any] => {
  const [subscriptionResources, loaded, loadError] =
    useSubscriptionResourceWatch({
      overrides: { managedClusters },
      drResources: {
        data: drResources,
        loaded: drLoaded,
        loadError: drLoadError,
      },
    });

  const drClusters: DRClusterKind[] = drResources?.drClusters;
  const drClusterAppsMap: DRClusterAppsMap = React.useMemo(() => {
    if (loaded && !loadError) {
      const uniqueAppKeys = new Set<string>();
      const managedClusterList = Array.isArray(managedClusters.data)
        ? managedClusters.data
        : [managedClusters.data];
      const drClusterAppsMap: DRClusterAppsMap = drClusters.reduce(
        (acc, drCluster) => {
          const clusterName = getName(drCluster);
          acc[clusterName] = {
            managedCluster: {},
            totalAppCount: 0,
            protectedApps: [],
          };
          return acc;
        },
        {} as DRClusterAppsMap
      );

      const processSubscription = (
        subscriptionResource: any,
        appNamespace: string
      ) => {
        const { application, subscriptionGroupInfo } =
          subscriptionResource || {};
        subscriptionGroupInfo?.forEach((subscriptionGroup) => {
          const { placementDecision, drInfo } = subscriptionGroup || {};
          const { drPlacementControl, drPolicy, drCluster } = drInfo || {};
          const deploymentClusters = findDeploymentClusters(
            placementDecision,
            drPlacementControl
          );

          deploymentClusters?.forEach((decisionCluster) => {
            if (drClusterAppsMap.hasOwnProperty(decisionCluster)) {
              const appKey = getAppUniqueId(
                getName(application),
                appNamespace,
                decisionCluster
              );

              const foundManagedCluster = managedClusterList.find(
                (managedCluster) => getName(managedCluster) === decisionCluster
              );
              const managedCluster = Array.isArray(foundManagedCluster)
                ? foundManagedCluster
                : [foundManagedCluster];

              subscriptionGroup.managedClusters = managedCluster;
              if (!uniqueAppKeys.has(appKey)) {
                uniqueAppKeys.add(appKey);
                drClusterAppsMap[decisionCluster].totalAppCount += 1;
              }

              const drpcSpec = drPlacementControl?.spec ?? {};
              const drpcStatus = drPlacementControl?.status ?? {};

              if (!_.isEmpty(drInfo)) {
                const protectedApp = {
                  appName: getName(application),
                  appNamespace,
                  appKind: application?.kind,
                  appAPIVersion: application?.apiVersion,
                  appType: APPLICATION_TYPE.SUBSCRIPTION,
                  placementInfo: [
                    {
                      deploymentClusterName: decisionCluster,
                      drpcName: getName(drPlacementControl),
                      drpcNamespace: getNamespace(drPlacementControl),
                      protectedPVCs:
                        getProtectedPVCsFromDRPC(drPlacementControl),
                      replicationType: findDRType(drCluster),
                      syncInterval: drPolicy?.spec?.schedulingInterval,
                      workloadNamespace: appNamespace,
                      failoverCluster: drpcSpec?.failoverCluster,
                      preferredCluster: drpcSpec?.preferredCluster,
                      lastGroupSyncTime: drpcStatus?.lastGroupSyncTime,
                      status: drpcStatus?.phase as DRPC_STATUS,
                    },
                  ],
                };

                const existingAppIndex = drClusterAppsMap[
                  decisionCluster
                ].protectedApps.findIndex(
                  (app) =>
                    app.appName === getName(application) &&
                    app.appNamespace === getNamespace(application)
                );

                if (existingAppIndex !== -1) {
                  drClusterAppsMap[decisionCluster].protectedApps[
                    existingAppIndex
                  ].placementInfo.push(protectedApp.placementInfo[0]);
                } else {
                  drClusterAppsMap[decisionCluster].protectedApps.push(
                    protectedApp
                  );
                }
              }
            }
          });
        });
      };

      subscriptionResources.forEach((subscriptionResource) => {
        const appNamespace =
          getNamespace(subscriptionResource?.application) || '';
        processSubscription(subscriptionResource, appNamespace);
      });
      return drClusterAppsMap;
    }
    return {};
  }, [
    drClusters,
    subscriptionResources,
    managedClusters.data,
    loaded,
    loadError,
  ]);

  return [drClusterAppsMap, loaded, loadError];
};

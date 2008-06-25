function [branchOrder,branchConnectivity,pointsConnectivity] =  getConnectivityANDOrder(orderInfo,segmentsNB,endings)

%builds the Connectivity and Order information about the segments


%global segmentsNB;
%global endings;

%BUILDING THE BRANCHES CONNECTIONS
%assuming a maximum order of 50
%flags for each order

connectivity=-5*ones(50,1);
currentOrder=0;
previousOrder=0;
branchConnectivity=[];
branchOrder=[];
difference=0;


%Initial conditions
branchOrder(1)=-1;
branchConnectivity(1)=-1;
pointsConnectivity(1)=-1;
connectivity(1) = 1;

for i=2:segmentsNB
    currentOrder = orderInfo(i);
    %currentOrder=length(find(orderInfo(i,:)>0));
    previousOrder = orderInfo(i-1);
    %previousOrder=length(find(orderInfo(i-1,:)>0));
    cO(i)=currentOrder;
    branchOrder=[branchOrder; currentOrder];

    if currentOrder==0
        branchConnectivity(i)=-1;
        pointsConnectivity(i)=-1;
        connectivity(1)=i;

    elseif(currentOrder<=previousOrder)
        difference=previousOrder-currentOrder;
        branchConnectivity(i)=connectivity(previousOrder-difference);
        pointsConnectivity(i)=endings(branchConnectivity(i));
    else
        branchConnectivity(i) = i-1;
        pointsConnectivity(i) = endings(i-1);

    end;
    connectivity(currentOrder+1)=i;
end;

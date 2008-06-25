function [RaveledNeuron URaveledNeuron RepairedNeuron Soma ApicalPoint n] = loadNewFileFormat(filename)

n = hdf5morph();
m = hdf5morph();
f1 = findstr(filename,'\');
f2 = findstr(filename,'/');
f = [f1 f2];
f = sort(f,'ascend');
path = filename(1:f(end)-1);
filename(1:f(end))=[];
n=load(n, path, filename);
if hasRawMorphology(n)
    structure = getStructure(n,'raw');
    points = get(n,'rawpoints');
    m = setRawMorphology(m,'','',points,structure);
    pointno=size(points,2);
    secno=size(structure,2);
    beginnings=structure(1,:)+1;      % directly from hdf5 file
    endings=structure(1,2:secno); % endings have to be inferred
    endings(secno)=pointno;         % last point has to be calculated differently...
    typeInfo=structure(2, :)-1;  % directly in hdf5 file yet, here soma has to equal 0
    % the index of the parent section in integer starting with 0
    branchcon=structure(3, :)+1;       %directly in hdf5 file
    for i=1:secno
        orderInfo(i) = traverseToRoot(branchcon, i);
    end
    if size(beginnings,1)<size(beginnings,2)
        points = points';
        beginnings = beginnings';
        endings = endings';
        typeInfo = typeInfo';
        branchcon = branchcon';
    end
    %create three different vectors for the dimensions
    X=points(:,1);
    Y=points(:,2);
    Z=points(:,3);
    Coordinates=[X Y Z];
    Diameter=points(:,4);
    segmentsNB=size(beginnings,1);
    %[branchOrder,branchConnectivity,pointsConnectivity] = getConnectivityANDOrder(orderInfo,segmentsNB,endings);
    if size(orderInfo,1)==1
        orderInfo=orderInfo';
    end
    branchOrder = orderInfo;
    branchConnectivity = branchcon';
    branchConnectivity(1)=-1;
    branchConnectivity(find(branchConnectivity==1))=-1;
    pointsConnectivity = zeros(size(branchConnectivity));
    pointsConnectivity(find(branchConnectivity~=-1))=endings(branchConnectivity(find(branchConnectivity~=-1)));
    pointsConnectivity(find(branchConnectivity==-1))=-1;
    temp = find (typeInfo==0);
    if isempty(temp)
        temp = find(branchOrder==0);
        temp = Coordinates(beginnings(temp),:);
    else
        temp = Coordinates(beginnings(temp):endings(temp),:);
    end;
    somaCenter =  mean(temp);
    somaSegment = find (typeInfo==0);
    initialSomaPoints = beginnings(somaSegment):endings(somaSegment);
    Soma.somaCenter = somaCenter;
    Soma.somaSegment = somaSegment;
    Soma.somaPoints = initialSomaPoints;

    RaveledNeuron.Coordinates = Coordinates;
    RaveledNeuron.X = X;
    RaveledNeuron.Y= Y;
    RaveledNeuron.Z = Z;
    RaveledNeuron.Diameter = Diameter;
    RaveledNeuron.beginnings = beginnings;
    RaveledNeuron.endings = endings;
    RaveledNeuron.typeInfo = typeInfo;
    RaveledNeuron.branchOrder = branchOrder;
    RaveledNeuron.branchConnectivity = branchConnectivity;
    RaveledNeuron.pointsConnectivity = pointsConnectivity;
    RaveledNeuron.segmentsNB = segmentsNB;
    RaveledNeuron.neuronPointsNB = size(Coordinates,1);

    [segmentsLength, segmentsDistance, segmentsNormDistance] = getLengthsANDDistances(RaveledNeuron);

    RaveledNeuron.segmentsLength = segmentsLength;
    RaveledNeuron.segmentsDistance = segmentsDistance;
    RaveledNeuron.segmentsNormDistance = segmentsNormDistance;
end
if hasUnraveledMorphology(n)
    structure = getStructure(n,'unraveled');
    points = get(n,'unraveledpoints');
    m = setUnraveledMorphology(m,'',points);
    secno=size(structure,2);
    beginnings=structure(1,:)+1;      % directly from hdf5 file
    endings=structure(1,2:secno); % endings have to be inferred
    endings(secno)=pointno;         % last point has to be calculated differently...
    typeInfo=structure(2, :)-1;  % directly in hdf5 file yet, here soma has to equal 0
    % the index of the parent section in integer starting with 0
    branchcon=structure(3, :)+1;       %directly in hdf5 file
    for i=1:secno
        orderInfo(i) = traverseToRoot(branchcon, i);
    end
    if size(beginnings,1)<size(beginnings,2)
        points = points';
        beginnings = beginnings';
        endings = endings';
        typeInfo = typeInfo';
        branchcon = branchcon';
    end
    %create three different vectors for the dimensions
    X=points(:,1);
    Y=points(:,2);
    Z=points(:,3);
    Coordinates=[X Y Z];
    Diameter=points(:,4);
    segmentsNB=size(beginnings,1);
    %[branchOrder,branchConnectivity,pointsConnectivity] = getConnectivityANDOrder(orderInfo,segmentsNB,endings);
    if size(orderInfo,1)==1
        orderInfo=orderInfo';
    end
    branchOrder = orderInfo;
    branchConnectivity = branchcon';
    branchConnectivity(1)=-1;
    branchConnectivity(find(branchConnectivity==1))=-1;
    pointsConnectivity = zeros(size(branchConnectivity));
    pointsConnectivity(find(branchConnectivity~=-1))=endings(branchConnectivity(find(branchConnectivity~=-1)));
    pointsConnectivity(find(branchConnectivity==-1))=-1;
    URaveledNeuron.Coordinates = Coordinates;
    URaveledNeuron.X = X;
    URaveledNeuron.Y= Y;
    URaveledNeuron.Z = Z;
    URaveledNeuron.Diameter = Diameter;
    URaveledNeuron.beginnings = beginnings;
    URaveledNeuron.endings = endings;
    URaveledNeuron.typeInfo = typeInfo;
    URaveledNeuron.branchOrder = branchOrder;
    URaveledNeuron.branchConnectivity = branchConnectivity;
    URaveledNeuron.pointsConnectivity = pointsConnectivity;
    URaveledNeuron.segmentsNB = segmentsNB;
    URaveledNeuron.neuronPointsNB = size(Coordinates,1);

    [segmentsLength, segmentsDistance, segmentsNormDistance] = getLengthsANDDistances(URaveledNeuron);

    URaveledNeuron.segmentsLength = segmentsLength;
    URaveledNeuron.segmentsDistance = segmentsDistance;
    URaveledNeuron.segmentsNormDistance = segmentsNormDistance;
end
if hasRepairedMorphology(n)
    structure = getStructure(n,'repaired');
    points = get(n,'repairedpoints');
    m = setRepairedMorphology(m,'',points,structure);
    pointno=size(points,2);
    secno=size(structure,2);
    beginnings=structure(1,:)+1;      % directly from hdf5 file
    endings=structure(1,2:secno); % endings have to be inferred
    endings(secno)=pointno;         % last point has to be calculated differently...
    typeInfo=structure(2, :)-1;  % directly in hdf5 file yet, here soma has to equal 0
    % the index of the parent section in integer starting with 0
    branchcon=structure(3, :)+1;       %directly in hdf5 file
    for i=1:secno
        orderInfo(i) = traverseToRoot(branchcon, i);
    end
    if size(beginnings,1)<size(beginnings,2)
        points = points';
        beginnings = beginnings';
        endings = endings';
        typeInfo = typeInfo';
        branchcon = branchcon';
    end
    %create three different vectors for the dimensions
    X=points(:,1);
    Y=points(:,2);
    Z=points(:,3);
    Coordinates=[X Y Z];
    Diameter=points(:,4);
    segmentsNB=size(beginnings,1);
    %[branchOrder,branchConnectivity,pointsConnectivity] = getConnectivityANDOrder(orderInfo,segmentsNB,endings);
    if size(orderInfo,1)==1
        orderInfo=orderInfo';
    end
    branchOrder = orderInfo;
    branchConnectivity = branchcon';
    branchConnectivity(1)=-1;
    branchConnectivity(find(branchConnectivity==1))=-1;
    pointsConnectivity = zeros(size(branchConnectivity));
    pointsConnectivity(find(branchConnectivity~=-1))=endings(branchConnectivity(find(branchConnectivity~=-1)));
    pointsConnectivity(find(branchConnectivity==-1))=-1;
    RepairedNeuron.Coordinates = Coordinates;
    RepairedNeuron.X = X;
    RepairedNeuron.Y= Y;
    RepairedNeuron.Z = Z;
    RepairedNeuron.Diameter = Diameter;
    RepairedNeuron.beginnings = beginnings;
    RepairedNeuron.endings = endings;
    RepairedNeuron.typeInfo = typeInfo;
    RepairedNeuron.branchOrder = branchOrder;
    RepairedNeuron.branchConnectivity = branchConnectivity;
    RepairedNeuron.pointsConnectivity = pointsConnectivity;
    RepairedNeuron.segmentsNB = segmentsNB;
    RepairedNeuron.neuronPointsNB = size(Coordinates,1);

    [segmentsLength, segmentsDistance, segmentsNormDistance] = getLengthsANDDistances(RepairedNeuron);

    RepairedNeuron.segmentsLength = segmentsLength;
    RepairedNeuron.segmentsDistance = segmentsDistance;
    RepairedNeuron.segmentsNormDistance = segmentsNormDistance;


end

ApicalPoint = get(n,'apical');
% recursively climb up in tree to see how many steps are required
% to reach the root node (ie. order of the branch)
% branches connected to the soma have first order (soma has 0 order)
% in order to change this change order=0 to order=-1
function order=traverseToRoot(branchcon, ind)

if (branchcon(ind) == 0)
    order = -1;
else
    order = traverseToRoot(branchcon, branchcon(ind)) + 1;
end
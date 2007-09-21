function getDendriteHeigths(filePath, path)
% function that plots histograms showing the maxDendriteHeights for each type of neurons
% done to compare dendrites heights for clones and repaired cells

%Types of neurons to be considered
neuronTypes = { 'SSC','L2PC','L3PC','L4PC','L4SP','L4SS','L5CSPC','L5CHPC','L6CTPC','L6CCPC','L6CSPC' };
%Number of these types
TypesNB = length(neuronTypes);

%******************LOAD THE FILES NEEDED

%load the morphology parameters file
fid = fopen(filePath);
A =textscan(fid,'%s%f%f%f%f%f%f%f%f');

%get info needed from morphology file (input file)
neuronName = A{1,1};
neuronName = strrep(neuronName,'.h5','');

maxHeightAxon = A{1,2};
maxHeightDendrite = A{1,4};
fclose(fid)

%***********************************

%load the NeuronDB.dat file
fid = fopen(path);
A = textscan(fid,'%s%d%s');

neuron = A{1,1};
layerNB = A{1,2};
type = A{1,3};

fclose(fid)

%***********************************

neuronsNB = length(neuron);

temp=zeros(1,neuronsNB);
for i=1:TypesNB
   cType = neuronTypes{i};
   cTypeIndices = strmatch(cType,type,'exact');
    %%%%%%%%%%%%%%%%%%%%%%%if clones removed%%%%%%%%%%%%%%%%%%%%%%%%%%%
%           i= strmatch ('L', neuron(cTypeIndices));
%           cTypeIndices(i)=[];
     %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
   if isempty(cTypeIndices)
       TEXT = sprintf(' ****************The are no cells defined as %s ****************',cType);
       disp(TEXT)
       continue   
   end
    temp(cTypeIndices)=-1; %assign a temp of -1 for neurons of all above types
end


for i=1:6
    %initializing
    MPIndices=[];
   
    indices = find (layerNB==i & temp'==-1); %get indices of above type in specific layer   
       
    if ~isempty(indices)
        MPIndices(indices)= getMorphIndices(indices, neuron, neuronName);%get corresponding indices in morphology file
        minus = find (MPIndices==0);
        MPIndices(minus)=[];
        
        
        
        x= 40:100:1400;
        subplot (3,2,i),hist (maxHeightDendrite(MPIndices),x)
        %print (gcf,'-depsc2','home')
                
        textTitle = sprintf('Layer %d',i);
        title(textTitle)
        xlabel('maxDendriteHeight')
        ylabel ('neurons')
       end
end


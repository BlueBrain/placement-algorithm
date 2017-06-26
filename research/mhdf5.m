%%Copyright © BBP/EPFL 2005-2011; All rights reserved. Do not distribute without further notice
function [points, beginnings, endings, typeInfo, orderInfo, branchcon] = mhdf5(filename)

% fileinfo = hdf5info('/home/anwar/cajal_neurons/C210301C1');
% points=hdf5read('/home/anwar/cajal_neurons/C210301C1', '/points'); %holds x,y,z,d
% structure=hdf5read('/home/anwar/cajal_neurons/C210301C1', '/structure'); %holds startpoint, type, parentid

points = hdf5read(filename,'/points');
structure = hdf5read(filename,'/structure');

%points = points';
%structure = structure';

pointno=size(points,2);
secno=size(structure,2);

beginnings=structure(1,:)+1;      % directly from hdf5 file
endings=structure(1,2:secno); % endings have to be inferred
endings(secno)=pointno;         % last point has to be calculated differently...

typeInfo=structure(2, :)-1;  % directly in hdf5 file yet, here soma has to equal 0

% the index of the parent section in integer starting with 0
branchcon=structure(3,:)+1;       %directly in hdf5 file

for i=1:secno
  orderInfo(i) = traverseToRoot(branchcon, i);
end
orderInfo = double(orderInfo');
typeInfo = double(typeInfo);
branchcon = double(branchcon);
points = double(points);
beginnings = double(beginnings);
endings = double(endings);

points = points';

%orderInfo=ones(secno,1);

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
